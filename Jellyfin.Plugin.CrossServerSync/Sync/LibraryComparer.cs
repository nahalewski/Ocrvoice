using Jellyfin.Plugin.CrossServerSync.Models;

namespace Jellyfin.Plugin.CrossServerSync.Sync;

/// <summary>
/// Compares two libraries purely on Jellyfin metadata (provider ids and
/// season/episode numbers), never on file names. Produces a
/// <see cref="ComparisonReport"/> describing what each side is missing.
/// </summary>
public static class LibraryComparer
{
    /// <summary>
    /// Compares local and remote catalogues.
    /// </summary>
    /// <param name="localMovies">Local movies.</param>
    /// <param name="remoteMovies">Remote movies.</param>
    /// <param name="localSeries">Local series with episodes.</param>
    /// <param name="remoteSeries">Remote series with episodes.</param>
    /// <param name="remoteServerName">Display name for the remote server.</param>
    /// <returns>The comparison report.</returns>
    public static ComparisonReport Compare(
        IReadOnlyList<MovieEntry> localMovies,
        IReadOnlyList<MovieEntry> remoteMovies,
        IReadOnlyList<SeriesEntry> localSeries,
        IReadOnlyList<SeriesEntry> remoteSeries,
        string remoteServerName)
    {
        var report = new ComparisonReport { RemoteServerName = remoteServerName };

        CompareMovies(localMovies, remoteMovies, report);
        CompareSeries(localSeries, remoteSeries, report);

        return report;
    }

    private static void CompareMovies(
        IReadOnlyList<MovieEntry> localMovies,
        IReadOnlyList<MovieEntry> remoteMovies,
        ComparisonReport report)
    {
        var localKeys = localMovies.Select(m => m.MatchKey).ToHashSet(StringComparer.Ordinal);
        var remoteKeys = remoteMovies.Select(m => m.MatchKey).ToHashSet(StringComparer.Ordinal);

        foreach (var movie in remoteMovies)
        {
            if (!localKeys.Contains(movie.MatchKey))
            {
                report.MoviesMissingLocally.Add(ToMissing(movie, ItemSide.Remote));
            }
        }

        foreach (var movie in localMovies)
        {
            if (!remoteKeys.Contains(movie.MatchKey))
            {
                report.MoviesMissingRemotely.Add(ToMissing(movie, ItemSide.Local));
            }
        }
    }

    private static void CompareSeries(
        IReadOnlyList<SeriesEntry> localSeries,
        IReadOnlyList<SeriesEntry> remoteSeries,
        ComparisonReport report)
    {
        var localByKey = Index(localSeries);
        var remoteByKey = Index(remoteSeries);

        // Missing on local = present on remote, absent (whole or partial) on local.
        foreach (var remote in remoteSeries)
        {
            localByKey.TryGetValue(remote.MatchKey, out var local);
            var gap = BuildGap(source: remote, target: local, sourceSide: ItemSide.Remote);
            if (gap is not null)
            {
                report.SeriesMissingLocally.Add(gap);
            }
        }

        // Missing on remote = present on local, absent (whole or partial) on remote.
        foreach (var local in localSeries)
        {
            remoteByKey.TryGetValue(local.MatchKey, out var remote);
            var gap = BuildGap(source: local, target: remote, sourceSide: ItemSide.Local);
            if (gap is not null)
            {
                report.SeriesMissingRemotely.Add(gap);
            }
        }
    }

    private static SeriesGap? BuildGap(SeriesEntry source, SeriesEntry? target, ItemSide sourceSide)
    {
        var targetEpisodeKeys = target is null
            ? new HashSet<string>(StringComparer.Ordinal)
            : target.Episodes
                .Select(e => MediaKey.ForEpisode(target.MatchKey, e))
                .ToHashSet(StringComparer.Ordinal);

        var targetSeasons = target is null
            ? new HashSet<int>()
            : target.Episodes
                .Where(e => e.SeasonNumber.HasValue)
                .Select(e => e.SeasonNumber!.Value)
                .ToHashSet();

        var missingEpisodes = new List<MissingItem>();
        var sourceSeasons = new HashSet<int>();

        foreach (var episode in source.Episodes)
        {
            if (episode.SeasonNumber.HasValue)
            {
                sourceSeasons.Add(episode.SeasonNumber.Value);
            }

            var episodeKey = MediaKey.ForEpisode(source.MatchKey, episode);
            if (!targetEpisodeKeys.Contains(episodeKey))
            {
                missingEpisodes.Add(new MissingItem
                {
                    Kind = MediaKind.Episode,
                    Title = episode.Name,
                    SeriesTitle = TitleWithYear(source.Name, source.ProductionYear),
                    SeasonNumber = episode.SeasonNumber,
                    EpisodeNumber = episode.EpisodeNumber,
                    MatchKey = episodeKey,
                    SourceItemId = episode.Id,
                    Source = sourceSide,
                    SizeBytes = episode.SizeBytes,
                    SourcePath = episode.Path
                });
            }
        }

        if (missingEpisodes.Count == 0)
        {
            return null;
        }

        var missingSeasons = sourceSeasons
            .Where(s => !targetSeasons.Contains(s))
            .OrderBy(s => s)
            .ToList();

        return new SeriesGap
        {
            SeriesTitle = TitleWithYear(source.Name, source.ProductionYear),
            MatchKey = source.MatchKey,
            SeriesEntirelyMissing = target is null,
            MissingSeasons = missingSeasons,
            MissingEpisodes = missingEpisodes
                .OrderBy(e => e.SeasonNumber ?? 0)
                .ThenBy(e => e.EpisodeNumber ?? 0)
                .ToList()
        };
    }

    private static Dictionary<string, SeriesEntry> Index(IReadOnlyList<SeriesEntry> series)
    {
        var dict = new Dictionary<string, SeriesEntry>(StringComparer.Ordinal);
        foreach (var entry in series)
        {
            // If two library folders expose the same series, merge their episodes.
            if (dict.TryGetValue(entry.MatchKey, out var existing))
            {
                existing.Episodes.AddRange(entry.Episodes);
            }
            else
            {
                dict[entry.MatchKey] = entry;
            }
        }

        return dict;
    }

    private static MissingItem ToMissing(MovieEntry movie, ItemSide side) => new()
    {
        Kind = MediaKind.Movie,
        Title = TitleWithYear(movie.Name, movie.ProductionYear),
        MatchKey = movie.MatchKey,
        SourceItemId = movie.Id,
        Source = side,
        SizeBytes = movie.SizeBytes,
        SourcePath = movie.Path
    };

    private static string TitleWithYear(string name, int? year) =>
        year.HasValue ? $"{name} ({year})" : name;
}
