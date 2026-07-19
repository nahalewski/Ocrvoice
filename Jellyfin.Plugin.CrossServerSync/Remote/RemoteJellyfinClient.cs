using System.Net.Http.Headers;
using System.Text.Json;
using Jellyfin.Plugin.CrossServerSync.Models;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.CrossServerSync.Remote;

/// <summary>
/// Thin REST client for a second Jellyfin server. Only the endpoints needed for
/// comparison and transfer are implemented, all authenticated with an API key.
/// </summary>
public class RemoteJellyfinClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    private readonly HttpClient _httpClient;
    private readonly ILogger _logger;
    private readonly string _baseUrl;
    private readonly string _apiKey;

    /// <summary>
    /// Initializes a new instance of the <see cref="RemoteJellyfinClient"/> class.
    /// </summary>
    /// <param name="httpClient">A shared HttpClient.</param>
    /// <param name="logger">Logger.</param>
    /// <param name="baseUrl">Remote base URL.</param>
    /// <param name="apiKey">Remote API key.</param>
    public RemoteJellyfinClient(HttpClient httpClient, ILogger logger, string baseUrl, string apiKey)
    {
        _httpClient = httpClient;
        _logger = logger;
        _baseUrl = (baseUrl ?? string.Empty).TrimEnd('/');
        _apiKey = apiKey ?? string.Empty;
    }

    /// <summary>Gets a value indicating whether the client is configured.</summary>
    public bool IsConfigured =>
        !string.IsNullOrWhiteSpace(_baseUrl) && !string.IsNullOrWhiteSpace(_apiKey);

    /// <summary>
    /// Verifies connectivity and authentication by reading public system info.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The server name on success; throws on failure.</returns>
    public async Task<string> PingAsync(CancellationToken cancellationToken)
    {
        using var request = CreateRequest(HttpMethod.Get, "/System/Info");
        using var response = await _httpClient.SendAsync(request, cancellationToken).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);
        return doc.RootElement.TryGetProperty("ServerName", out var name)
            ? name.GetString() ?? "Jellyfin"
            : "Jellyfin";
    }

    /// <summary>Fetches all movies on the remote server.</summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The remote movies.</returns>
    public async Task<List<MovieEntry>> GetMoviesAsync(CancellationToken cancellationToken)
    {
        var url = "/Items?Recursive=true&IncludeItemTypes=Movie&IsMissing=false" +
                  "&Fields=ProviderIds,Path,MediaSources";
        var items = await GetItemsAsync(url, cancellationToken).ConfigureAwait(false);
        var movies = new List<MovieEntry>();
        foreach (var item in items)
        {
            movies.Add(new MovieEntry
            {
                Id = GetString(item, "Id"),
                Name = GetString(item, "Name"),
                ProductionYear = GetInt(item, "ProductionYear"),
                ProviderIds = GetProviderIds(item),
                Path = GetStringOrNull(item, "Path"),
                SizeBytes = GetMediaSize(item),
                Container = GetContainer(item)
            });
        }

        return movies;
    }

    /// <summary>
    /// Fetches all series and their episodes on the remote server.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The remote series with populated episodes.</returns>
    public async Task<List<SeriesEntry>> GetSeriesWithEpisodesAsync(CancellationToken cancellationToken)
    {
        var seriesUrl = "/Items?Recursive=true&IncludeItemTypes=Series&Fields=ProviderIds";
        var seriesItems = await GetItemsAsync(seriesUrl, cancellationToken).ConfigureAwait(false);

        var series = new Dictionary<string, SeriesEntry>(StringComparer.Ordinal);
        foreach (var item in seriesItems)
        {
            var entry = new SeriesEntry
            {
                Id = GetString(item, "Id"),
                Name = GetString(item, "Name"),
                ProductionYear = GetInt(item, "ProductionYear"),
                ProviderIds = GetProviderIds(item)
            };
            series[entry.Id] = entry;
        }

        var episodeUrl = "/Items?Recursive=true&IncludeItemTypes=Episode&IsMissing=false" +
                         "&Fields=ProviderIds,Path,MediaSources,ParentId";
        var episodeItems = await GetItemsAsync(episodeUrl, cancellationToken).ConfigureAwait(false);
        foreach (var item in episodeItems)
        {
            var seriesId = GetStringOrNull(item, "SeriesId");
            if (seriesId is null || !series.TryGetValue(seriesId, out var parent))
            {
                continue;
            }

            parent.Episodes.Add(new EpisodeEntry
            {
                Id = GetString(item, "Id"),
                Name = GetString(item, "Name"),
                SeasonNumber = GetInt(item, "ParentIndexNumber"),
                EpisodeNumber = GetInt(item, "IndexNumber"),
                Path = GetStringOrNull(item, "Path"),
                SizeBytes = GetMediaSize(item),
                Container = GetContainer(item)
            });
        }

        return series.Values.ToList();
    }

    /// <summary>
    /// Opens a download stream for a remote item's primary media file.
    /// </summary>
    /// <param name="itemId">The remote item id.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The HTTP response; caller disposes it and reads the content stream.</returns>
    public async Task<HttpResponseMessage> OpenDownloadStreamAsync(string itemId, CancellationToken cancellationToken)
    {
        using var request = CreateRequest(HttpMethod.Get, $"/Items/{itemId}/Download");
        var response = await _httpClient
            .SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken)
            .ConfigureAwait(false);
        response.EnsureSuccessStatusCode();
        return response;
    }

    private async Task<List<JsonElement>> GetItemsAsync(string relativeUrl, CancellationToken cancellationToken)
    {
        using var request = CreateRequest(HttpMethod.Get, relativeUrl);
        using var response = await _httpClient.SendAsync(request, cancellationToken).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);
        var result = new List<JsonElement>();
        if (doc.RootElement.TryGetProperty("Items", out var itemsElement) &&
            itemsElement.ValueKind == JsonValueKind.Array)
        {
            foreach (var element in itemsElement.EnumerateArray())
            {
                // Clone so the elements outlive the JsonDocument disposal.
                result.Add(element.Clone());
            }
        }

        return result;
    }

    private HttpRequestMessage CreateRequest(HttpMethod method, string relativeUrl)
    {
        var request = new HttpRequestMessage(method, _baseUrl + relativeUrl);
        request.Headers.Authorization = new AuthenticationHeaderValue(
            "MediaBrowser",
            $"Token=\"{_apiKey}\", Client=\"CrossServerSync\", Device=\"Jellyfin\", DeviceId=\"cross-server-sync\", Version=\"1.0.0\"");
        request.Headers.TryAddWithoutValidation("X-Emby-Token", _apiKey);
        return request;
    }

    private static Dictionary<string, string> GetProviderIds(JsonElement item)
    {
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        if (item.TryGetProperty("ProviderIds", out var providers) &&
            providers.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in providers.EnumerateObject())
            {
                var value = property.Value.GetString();
                if (!string.IsNullOrWhiteSpace(value))
                {
                    result[property.Name] = value;
                }
            }
        }

        return result;
    }

    private static long? GetMediaSize(JsonElement item)
    {
        if (item.TryGetProperty("MediaSources", out var sources) &&
            sources.ValueKind == JsonValueKind.Array)
        {
            foreach (var source in sources.EnumerateArray())
            {
                if (source.TryGetProperty("Size", out var size) &&
                    size.ValueKind == JsonValueKind.Number &&
                    size.TryGetInt64(out var value))
                {
                    return value;
                }
            }
        }

        return null;
    }

    private static string? GetContainer(JsonElement item)
    {
        if (item.TryGetProperty("MediaSources", out var sources) &&
            sources.ValueKind == JsonValueKind.Array)
        {
            foreach (var source in sources.EnumerateArray())
            {
                if (source.TryGetProperty("Container", out var container))
                {
                    var value = container.GetString();
                    if (!string.IsNullOrWhiteSpace(value))
                    {
                        return value;
                    }
                }
            }
        }

        // Fall back to the file extension from the path.
        var path = GetStringOrNull(item, "Path");
        if (!string.IsNullOrWhiteSpace(path))
        {
            var ext = System.IO.Path.GetExtension(path);
            if (!string.IsNullOrWhiteSpace(ext))
            {
                return ext.TrimStart('.');
            }
        }

        return null;
    }

    private static string GetString(JsonElement item, string property) =>
        GetStringOrNull(item, property) ?? string.Empty;

    private static string? GetStringOrNull(JsonElement item, string property) =>
        item.TryGetProperty(property, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    private static int? GetInt(JsonElement item, string property)
    {
        if (item.TryGetProperty(property, out var value) &&
            value.ValueKind == JsonValueKind.Number &&
            value.TryGetInt32(out var result))
        {
            return result;
        }

        return null;
    }
}
