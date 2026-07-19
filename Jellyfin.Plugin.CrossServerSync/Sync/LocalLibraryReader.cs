using Jellyfin.Data.Enums;
using Jellyfin.Plugin.CrossServerSync.Models;
using MediaBrowser.Controller.Entities;
using MediaBrowser.Controller.Entities.Movies;
using MediaBrowser.Controller.Entities.TV;
using MediaBrowser.Controller.Library;

namespace Jellyfin.Plugin.CrossServerSync.Sync;

/// <summary>
/// Reads the local server's movie and TV libraries through
/// <see cref="ILibraryManager"/> and maps them to the shared models.
/// </summary>
public class LocalLibraryReader
{
    private readonly ILibraryManager _libraryManager;

    /// <summary>
    /// Initializes a new instance of the <see cref="LocalLibraryReader"/> class.
    /// </summary>
    /// <param name="libraryManager">The library manager.</param>
    public LocalLibraryReader(ILibraryManager libraryManager)
    {
        _libraryManager = libraryManager;
    }

    /// <summary>Reads all local movies.</summary>
    /// <returns>The local movies.</returns>
    public List<MovieEntry> GetMovies()
    {
        var query = new InternalItemsQuery
        {
            IncludeItemTypes = new[] { BaseItemKind.Movie },
            Recursive = true,
            IsVirtualItem = false
        };

        var result = new List<MovieEntry>();
        foreach (var item in _libraryManager.GetItemList(query))
        {
            if (item is not Movie movie)
            {
                continue;
            }

            result.Add(new MovieEntry
            {
                Id = movie.Id.ToString("N"),
                Name = movie.Name ?? string.Empty,
                ProductionYear = movie.ProductionYear,
                ProviderIds = new Dictionary<string, string>(movie.ProviderIds, StringComparer.OrdinalIgnoreCase),
                Path = movie.Path,
                SizeBytes = TryGetFileSize(movie.Path),
                Container = GetContainer(movie.Path, movie.Container)
            });
        }

        return result;
    }

    /// <summary>Reads all local series with their episodes.</summary>
    /// <returns>The local series.</returns>
    public List<SeriesEntry> GetSeriesWithEpisodes()
    {
        var seriesQuery = new InternalItemsQuery
        {
            IncludeItemTypes = new[] { BaseItemKind.Series },
            Recursive = true,
            IsVirtualItem = false
        };

        var seriesById = new Dictionary<Guid, SeriesEntry>();
        foreach (var item in _libraryManager.GetItemList(seriesQuery))
        {
            if (item is not Series series)
            {
                continue;
            }

            seriesById[series.Id] = new SeriesEntry
            {
                Id = series.Id.ToString("N"),
                Name = series.Name ?? string.Empty,
                ProductionYear = series.ProductionYear,
                ProviderIds = new Dictionary<string, string>(series.ProviderIds, StringComparer.OrdinalIgnoreCase)
            };
        }

        var episodeQuery = new InternalItemsQuery
        {
            IncludeItemTypes = new[] { BaseItemKind.Episode },
            Recursive = true,
            IsVirtualItem = false
        };

        foreach (var item in _libraryManager.GetItemList(episodeQuery))
        {
            if (item is not Episode episode || episode.SeriesId == Guid.Empty)
            {
                continue;
            }

            if (!seriesById.TryGetValue(episode.SeriesId, out var parent))
            {
                continue;
            }

            parent.Episodes.Add(new EpisodeEntry
            {
                Id = episode.Id.ToString("N"),
                Name = episode.Name ?? string.Empty,
                SeasonNumber = episode.ParentIndexNumber,
                EpisodeNumber = episode.IndexNumber,
                Path = episode.Path,
                SizeBytes = TryGetFileSize(episode.Path),
                Container = GetContainer(episode.Path, episode.Container)
            });
        }

        return seriesById.Values.ToList();
    }

    private static long? TryGetFileSize(string? path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return null;
        }

        try
        {
            var info = new FileInfo(path);
            return info.Exists ? info.Length : null;
        }
        catch
        {
            return null;
        }
    }

    private static string? GetContainer(string? path, string? container)
    {
        if (!string.IsNullOrWhiteSpace(container))
        {
            return container;
        }

        if (!string.IsNullOrWhiteSpace(path))
        {
            var ext = Path.GetExtension(path);
            if (!string.IsNullOrWhiteSpace(ext))
            {
                return ext.TrimStart('.');
            }
        }

        return null;
    }
}
