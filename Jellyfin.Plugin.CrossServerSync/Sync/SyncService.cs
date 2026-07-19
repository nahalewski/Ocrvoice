using Jellyfin.Plugin.CrossServerSync.Configuration;
using Jellyfin.Plugin.CrossServerSync.Models;
using Jellyfin.Plugin.CrossServerSync.Remote;
using MediaBrowser.Common.Net;
using MediaBrowser.Controller.Library;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.CrossServerSync.Sync;

/// <summary>
/// Orchestrates comparison and transfer between the local server and the
/// configured remote server.
///
/// Transfers always <em>pull</em> files down to the local disk (the only disk
/// this plugin can write to). To fill gaps on the remote server, run this same
/// plugin on that server pointed back at this one — the design is symmetric.
/// </summary>
public class SyncService
{
    private readonly ILibraryManager _libraryManager;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger _logger;
    private readonly LocalLibraryReader _localReader;
    private readonly DestinationResolver _destinationResolver;

    /// <summary>
    /// Initializes a new instance of the <see cref="SyncService"/> class.
    /// </summary>
    /// <param name="libraryManager">The library manager.</param>
    /// <param name="httpClientFactory">HTTP client factory.</param>
    /// <param name="logger">Logger.</param>
    public SyncService(
        ILibraryManager libraryManager,
        IHttpClientFactory httpClientFactory,
        ILogger<SyncService> logger)
    {
        _libraryManager = libraryManager;
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        _localReader = new LocalLibraryReader(libraryManager);
        _destinationResolver = new DestinationResolver(libraryManager, logger);
    }

    private static PluginConfiguration Config =>
        Plugin.Instance?.Configuration ?? new PluginConfiguration();

    /// <summary>
    /// Verifies the remote connection is reachable and authenticated.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>A tuple of success flag and message.</returns>
    public async Task<(bool Success, string Message)> TestConnectionAsync(CancellationToken cancellationToken)
    {
        var config = Config;
        var client = CreateRemoteClient(config);
        if (!client.IsConfigured)
        {
            return (false, "Remote server URL and API key are required.");
        }

        try
        {
            var name = await client.PingAsync(cancellationToken).ConfigureAwait(false);
            return (true, $"Connected to '{name}'.");
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Remote connection test failed");
            return (false, $"Connection failed: {ex.Message}");
        }
    }

    /// <summary>
    /// Reads both libraries and returns a comparison report.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The report.</returns>
    public async Task<ComparisonReport> CompareAsync(CancellationToken cancellationToken)
    {
        var config = Config;
        var client = CreateRemoteClient(config);
        if (!client.IsConfigured)
        {
            return new ComparisonReport
            {
                RemoteServerName = config.RemoteServerName,
                Error = "Remote server is not configured. Set the URL and API key first."
            };
        }

        try
        {
            var remoteName = await client.PingAsync(cancellationToken).ConfigureAwait(false);

            var localMovies = _localReader.GetMovies();
            var localSeries = _localReader.GetSeriesWithEpisodes();
            var remoteMovies = await client.GetMoviesAsync(cancellationToken).ConfigureAwait(false);
            var remoteSeries = await client.GetSeriesWithEpisodesAsync(cancellationToken).ConfigureAwait(false);

            _logger.LogInformation(
                "Comparison: local {LocalMovies} movies / {LocalSeries} series, " +
                "remote {RemoteMovies} movies / {RemoteSeries} series.",
                localMovies.Count,
                localSeries.Count,
                remoteMovies.Count,
                remoteSeries.Count);

            var name = string.IsNullOrWhiteSpace(config.RemoteServerName)
                ? remoteName
                : config.RemoteServerName;

            return LibraryComparer.Compare(localMovies, remoteMovies, localSeries, remoteSeries, name);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Comparison failed");
            return new ComparisonReport
            {
                RemoteServerName = config.RemoteServerName,
                Error = $"Comparison failed: {ex.Message}"
            };
        }
    }

    /// <summary>
    /// Runs a full sync: compares, then pulls every item missing locally that the
    /// direction setting allows, respecting the reserved free-space floor and the
    /// no-overwrite rule.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The run result.</returns>
    public async Task<SyncRunResult> SyncAllAsync(CancellationToken cancellationToken)
    {
        var report = await CompareAsync(cancellationToken).ConfigureAwait(false);
        if (report.Error is not null)
        {
            return new SyncRunResult { Message = report.Error };
        }

        var toPull = CollectPullTargets(report);
        return await TransferAsync(toPull, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Transfers a specific set of missing items (all of which must live on the
    /// remote server so they can be pulled locally).
    /// </summary>
    /// <param name="items">Items to pull.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The run result.</returns>
    public async Task<SyncRunResult> TransferAsync(
        IReadOnlyList<MissingItem> items,
        CancellationToken cancellationToken)
    {
        var config = Config;
        var result = new SyncRunResult();
        var client = CreateRemoteClient(config);
        if (!client.IsConfigured)
        {
            result.Message = "Remote server is not configured.";
            return result;
        }

        var storageGuard = new StorageGuard(config.ReservedSpaceGb, _logger);
        var movieRoot = _destinationResolver.ResolveMovieRoot(config);
        var tvRoot = _destinationResolver.ResolveTvRoot(config);

        // Snapshot the local match keys so we never re-copy something already
        // present under a different file name (metadata-based overwrite protection).
        var presentKeys = BuildLocalKeySet();

        var copiedAny = false;
        foreach (var item in items)
        {
            cancellationToken.ThrowIfCancellationRequested();

            if (item.Source != ItemSide.Remote)
            {
                // Cannot push to a remote disk over the API; skip.
                continue;
            }

            if (presentKeys.Contains(item.MatchKey))
            {
                result.Results.Add(Skip(item, TransferStatus.SkippedAlreadyPresent,
                    "A metadata match already exists locally."));
                continue;
            }

            var root = item.Kind == MediaKind.Movie ? movieRoot : tvRoot;
            if (string.IsNullOrWhiteSpace(root))
            {
                result.Results.Add(Skip(item, TransferStatus.SkippedNoDestination,
                    $"No {(item.Kind == MediaKind.Movie ? "movie" : "TV")} library folder configured."));
                continue;
            }

            var destination = item.Kind == MediaKind.Movie
                ? _destinationResolver.BuildMoviePath(root, item)
                : _destinationResolver.BuildEpisodePath(root, item);

            if (File.Exists(destination))
            {
                // Never overwrite an existing file.
                presentKeys.Add(item.MatchKey);
                result.Results.Add(Skip(item, TransferStatus.SkippedAlreadyPresent,
                    "Destination file already exists; left untouched."));
                continue;
            }

            var transfer = await CopyItemAsync(client, item, destination, storageGuard, cancellationToken)
                .ConfigureAwait(false);
            result.Results.Add(transfer);

            if (transfer.Status == TransferStatus.Copied)
            {
                copiedAny = true;
                presentKeys.Add(item.MatchKey);
            }
            else if (transfer.Status == TransferStatus.SkippedInsufficientSpace)
            {
                // Once the floor is hit, further copies to the same drive will also
                // fail; stop early to avoid noise but keep already-queued reports.
                _logger.LogInformation("Reserved space floor reached; stopping transfers.");
                result.Message = "Stopped: reserved free-space floor reached on the target drive.";
                break;
            }
        }

        if (copiedAny && config.RefreshLibraryAfterSync)
        {
            await RefreshLibraryAsync(cancellationToken).ConfigureAwait(false);
        }

        return result;
    }

    /// <summary>
    /// Collects the items eligible to be pulled to the local server based on the
    /// configured direction.
    /// </summary>
    /// <param name="report">The comparison report.</param>
    /// <returns>Items to pull.</returns>
    public static List<MissingItem> CollectPullTargets(ComparisonReport report)
    {
        var direction = Config.Direction;
        var items = new List<MissingItem>();

        if (direction is SyncDirection.PullFromRemote or SyncDirection.Bidirectional)
        {
            items.AddRange(report.MoviesMissingLocally);
            foreach (var gap in report.SeriesMissingLocally)
            {
                items.AddRange(gap.MissingEpisodes);
            }
        }

        return items;
    }

    private async Task<TransferResult> CopyItemAsync(
        RemoteJellyfinClient client,
        MissingItem item,
        string destination,
        StorageGuard storageGuard,
        CancellationToken cancellationToken)
    {
        var tempPath = destination + ".partial-" + Guid.NewGuid().ToString("N")[..8];
        try
        {
            using var response = await client.OpenDownloadStreamAsync(item.SourceItemId, cancellationToken)
                .ConfigureAwait(false);

            var size = response.Content.Headers.ContentLength ?? item.SizeBytes ?? 0;
            if (!storageGuard.CanFit(destination, size))
            {
                return Skip(item, TransferStatus.SkippedInsufficientSpace,
                    "Would breach the reserved free-space floor.");
            }

            var directory = Path.GetDirectoryName(destination);
            if (!string.IsNullOrWhiteSpace(directory))
            {
                Directory.CreateDirectory(directory);
            }

            long written;
            await using (var source = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false))
            await using (var target = new FileStream(tempPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                written = await CopyWithGuardAsync(source, target, destination, storageGuard, cancellationToken)
                    .ConfigureAwait(false);
            }

            if (written < 0)
            {
                TryDelete(tempPath);
                return Skip(item, TransferStatus.SkippedInsufficientSpace,
                    "Reserved free-space floor reached during copy; partial file removed.");
            }

            // Final guard against a race: never overwrite.
            if (File.Exists(destination))
            {
                TryDelete(tempPath);
                return Skip(item, TransferStatus.SkippedAlreadyPresent,
                    "Destination appeared during transfer; left untouched.");
            }

            File.Move(tempPath, destination);
            _logger.LogInformation("Copied {Title} -> {Destination} ({Bytes} bytes)",
                item.Title, destination, written);

            return new TransferResult
            {
                Item = item,
                Status = TransferStatus.Copied,
                DestinationPath = destination,
                BytesWritten = written,
                Message = "Copied."
            };
        }
        catch (Exception ex)
        {
            TryDelete(tempPath);
            _logger.LogError(ex, "Failed to copy {Title}", item.Title);
            return new TransferResult
            {
                Item = item,
                Status = TransferStatus.Failed,
                Message = ex.Message
            };
        }
    }

    private static async Task<long> CopyWithGuardAsync(
        Stream source,
        Stream target,
        string destination,
        StorageGuard storageGuard,
        CancellationToken cancellationToken)
    {
        var buffer = new byte[1024 * 1024];
        long total = 0;
        var sinceCheck = 0L;
        int read;
        while ((read = await source.ReadAsync(buffer, cancellationToken).ConfigureAwait(false)) > 0)
        {
            await target.WriteAsync(buffer.AsMemory(0, read), cancellationToken).ConfigureAwait(false);
            total += read;
            sinceCheck += read;

            // Re-check free space periodically for streams of unknown length.
            if (sinceCheck >= 512L * 1024 * 1024)
            {
                sinceCheck = 0;
                var available = storageGuard.GetAvailableBytes(destination);
                if (available is not null && available.Value <= storageGuard.ReservedBytes)
                {
                    return -1;
                }
            }
        }

        await target.FlushAsync(cancellationToken).ConfigureAwait(false);
        return total;
    }

    private HashSet<string> BuildLocalKeySet()
    {
        var keys = new HashSet<string>(StringComparer.Ordinal);
        foreach (var movie in _localReader.GetMovies())
        {
            keys.Add(movie.MatchKey);
        }

        foreach (var series in _localReader.GetSeriesWithEpisodes())
        {
            foreach (var episode in series.Episodes)
            {
                keys.Add(MediaKey.ForEpisode(series.MatchKey, episode));
            }
        }

        return keys;
    }

    private async Task RefreshLibraryAsync(CancellationToken cancellationToken)
    {
        try
        {
            await _libraryManager
                .ValidateMediaLibrary(new Progress<double>(), cancellationToken)
                .ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Library refresh after sync failed");
        }
    }

    private RemoteJellyfinClient CreateRemoteClient(PluginConfiguration config)
    {
        var httpClient = _httpClientFactory.CreateClient(NamedClient.Default);
        httpClient.Timeout = TimeSpan.FromMinutes(30);
        return new RemoteJellyfinClient(httpClient, _logger, config.RemoteServerUrl, config.RemoteApiKey);
    }

    private static TransferResult Skip(MissingItem item, TransferStatus status, string message) => new()
    {
        Item = item,
        Status = status,
        Message = message
    };

    private static void TryDelete(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
        catch
        {
            // best effort
        }
    }
}
