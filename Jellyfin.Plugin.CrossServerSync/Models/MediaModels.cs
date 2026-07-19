namespace Jellyfin.Plugin.CrossServerSync.Models;

/// <summary>
/// A normalized representation of a movie on either server, keyed on the
/// metadata Jellyfin assigns rather than on the file name.
/// </summary>
public class MovieEntry
{
    /// <summary>Gets or sets the Jellyfin item id on its home server.</summary>
    public string Id { get; set; } = string.Empty;

    /// <summary>Gets or sets the movie name.</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>Gets or sets the production year.</summary>
    public int? ProductionYear { get; set; }

    /// <summary>Gets or sets the provider ids (Tmdb, Imdb, etc.).</summary>
    public Dictionary<string, string> ProviderIds { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Gets or sets the source file path (on the item's home server).</summary>
    public string? Path { get; set; }

    /// <summary>Gets or sets the file size in bytes, if known.</summary>
    public long? SizeBytes { get; set; }

    /// <summary>Gets or sets the container / file extension, e.g. "mkv".</summary>
    public string? Container { get; set; }

    /// <summary>
    /// A stable matching key built from provider ids (preferred) or name+year.
    /// </summary>
    public string MatchKey => MediaKey.ForMovie(this);
}

/// <summary>
/// A normalized representation of a series on either server.
/// </summary>
public class SeriesEntry
{
    /// <summary>Gets or sets the Jellyfin series id on its home server.</summary>
    public string Id { get; set; } = string.Empty;

    /// <summary>Gets or sets the series name.</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>Gets or sets the first-air year.</summary>
    public int? ProductionYear { get; set; }

    /// <summary>Gets or sets the provider ids (Tvdb, Tmdb, Imdb, etc.).</summary>
    public Dictionary<string, string> ProviderIds { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Gets or sets the episodes belonging to this series.</summary>
    public List<EpisodeEntry> Episodes { get; set; } = new();

    /// <summary>A stable matching key for the series.</summary>
    public string MatchKey => MediaKey.ForSeries(this);
}

/// <summary>
/// A normalized representation of an episode.
/// </summary>
public class EpisodeEntry
{
    /// <summary>Gets or sets the Jellyfin episode id on its home server.</summary>
    public string Id { get; set; } = string.Empty;

    /// <summary>Gets or sets the episode name.</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>Gets or sets the season number.</summary>
    public int? SeasonNumber { get; set; }

    /// <summary>Gets or sets the episode number within the season.</summary>
    public int? EpisodeNumber { get; set; }

    /// <summary>Gets or sets the source file path (on the item's home server).</summary>
    public string? Path { get; set; }

    /// <summary>Gets or sets the file size in bytes, if known.</summary>
    public long? SizeBytes { get; set; }

    /// <summary>Gets or sets the container / file extension, e.g. "mkv".</summary>
    public string? Container { get; set; }
}

/// <summary>
/// Builds stable match keys from metadata. This is the heart of the
/// "match by metadata, not by file name" requirement.
/// </summary>
public static class MediaKey
{
    // Provider ids are checked in priority order. The first present id wins so
    // that the same logical item matches across servers regardless of file name.
    private static readonly string[] MovieProviders = { "Tmdb", "Imdb", "TmdbCollection" };
    private static readonly string[] SeriesProviders = { "Tvdb", "Tmdb", "Imdb" };

    /// <summary>Builds a match key for a movie.</summary>
    /// <param name="movie">The movie.</param>
    /// <returns>A normalized key.</returns>
    public static string ForMovie(MovieEntry movie)
    {
        foreach (var provider in MovieProviders)
        {
            if (movie.ProviderIds.TryGetValue(provider, out var id) && !string.IsNullOrWhiteSpace(id))
            {
                return $"movie:{provider.ToLowerInvariant()}:{id.Trim().ToLowerInvariant()}";
            }
        }

        return $"movie:title:{Normalize(movie.Name)}:{movie.ProductionYear?.ToString() ?? "0"}";
    }

    /// <summary>Builds a match key for a series.</summary>
    /// <param name="series">The series.</param>
    /// <returns>A normalized key.</returns>
    public static string ForSeries(SeriesEntry series)
    {
        foreach (var provider in SeriesProviders)
        {
            if (series.ProviderIds.TryGetValue(provider, out var id) && !string.IsNullOrWhiteSpace(id))
            {
                return $"series:{provider.ToLowerInvariant()}:{id.Trim().ToLowerInvariant()}";
            }
        }

        return $"series:title:{Normalize(series.Name)}:{series.ProductionYear?.ToString() ?? "0"}";
    }

    /// <summary>
    /// Builds a match key for an episode, scoped to its series. Episodes are
    /// matched on season + episode number, which is what Jellyfin uses to line
    /// up episodes across differently named files.
    /// </summary>
    /// <param name="seriesKey">The parent series match key.</param>
    /// <param name="episode">The episode.</param>
    /// <returns>A normalized key.</returns>
    public static string ForEpisode(string seriesKey, EpisodeEntry episode)
    {
        var season = episode.SeasonNumber?.ToString("D2") ?? "XX";
        var number = episode.EpisodeNumber?.ToString("D3") ?? "XXX";
        return $"{seriesKey}|s{season}e{number}";
    }

    private static string Normalize(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return string.Empty;
        }

        var chars = value.Trim().ToLowerInvariant()
            .Where(c => char.IsLetterOrDigit(c) || c == ' ')
            .ToArray();
        return new string(chars).Replace("  ", " ", StringComparison.Ordinal);
    }
}
