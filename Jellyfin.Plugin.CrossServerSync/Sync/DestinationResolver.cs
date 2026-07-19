using Jellyfin.Plugin.CrossServerSync.Configuration;
using Jellyfin.Plugin.CrossServerSync.Models;
using MediaBrowser.Controller.Library;
using MediaBrowser.Model.Entities;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.CrossServerSync.Sync;

/// <summary>
/// Works out where a transferred file should land on the local disk so that
/// Jellyfin's scanner recognises it. This is the "aware of folder structuring"
/// requirement: movies go into <c>Movie Name (Year)/</c> folders and episodes
/// into <c>Series Name (Year)/Season NN/</c> folders.
/// </summary>
public class DestinationResolver
{
    private readonly ILibraryManager _libraryManager;
    private readonly ILogger _logger;

    /// <summary>
    /// Initializes a new instance of the <see cref="DestinationResolver"/> class.
    /// </summary>
    /// <param name="libraryManager">The library manager.</param>
    /// <param name="logger">Logger.</param>
    public DestinationResolver(ILibraryManager libraryManager, ILogger logger)
    {
        _libraryManager = libraryManager;
        _logger = logger;
    }

    /// <summary>
    /// Resolves the root folder for movie storage. Uses the configured override
    /// if set, otherwise the first movie library folder.
    /// </summary>
    /// <param name="config">Plugin config.</param>
    /// <returns>The root path, or null if none can be found.</returns>
    public string? ResolveMovieRoot(PluginConfiguration config)
    {
        if (!string.IsNullOrWhiteSpace(config.MovieDestinationPath))
        {
            return config.MovieDestinationPath;
        }

        return FindLibraryRoot("movies");
    }

    /// <summary>
    /// Resolves the root folder for TV storage. Uses the configured override
    /// if set, otherwise the first TV library folder.
    /// </summary>
    /// <param name="config">Plugin config.</param>
    /// <returns>The root path, or null if none can be found.</returns>
    public string? ResolveTvRoot(PluginConfiguration config)
    {
        if (!string.IsNullOrWhiteSpace(config.TvDestinationPath))
        {
            return config.TvDestinationPath;
        }

        return FindLibraryRoot("tvshows");
    }

    /// <summary>
    /// Builds the full destination path for a missing movie.
    /// </summary>
    /// <param name="root">The movie library root.</param>
    /// <param name="item">The missing movie.</param>
    /// <returns>The absolute destination file path.</returns>
    public string BuildMoviePath(string root, MissingItem item)
    {
        var folderName = Sanitize(BuildTitleWithYear(item.Title));
        var extension = ResolveExtension(item.SourcePath);
        var fileName = $"{folderName}{extension}";
        return Path.Combine(root, folderName, fileName);
    }

    /// <summary>
    /// Builds the full destination path for a missing episode, including the
    /// series folder and <c>Season NN</c> subfolder.
    /// </summary>
    /// <param name="root">The TV library root.</param>
    /// <param name="item">The missing episode.</param>
    /// <returns>The absolute destination file path.</returns>
    public string BuildEpisodePath(string root, MissingItem item)
    {
        var seriesFolder = Sanitize(item.SeriesTitle ?? "Unknown Series");
        var season = item.SeasonNumber ?? 0;
        var seasonFolder = season == 0 ? "Specials" : $"Season {season:D2}";
        var extension = ResolveExtension(item.SourcePath);

        var seasonToken = $"S{season:D2}";
        var episodeToken = item.EpisodeNumber.HasValue ? $"E{item.EpisodeNumber.Value:D2}" : "E00";
        var episodeTitle = string.IsNullOrWhiteSpace(item.Title) ? string.Empty : $" - {item.Title}";
        var fileName = Sanitize($"{StripYear(seriesFolder)} - {seasonToken}{episodeToken}{episodeTitle}") + extension;

        return Path.Combine(root, seriesFolder, seasonFolder, fileName);
    }

    private string? FindLibraryRoot(string collectionType)
    {
        try
        {
            foreach (var folder in _libraryManager.GetVirtualFolders())
            {
                var type = folder.CollectionType?.ToString();
                if (type is not null &&
                    type.Equals(collectionType, StringComparison.OrdinalIgnoreCase) &&
                    folder.Locations is { Length: > 0 })
                {
                    foreach (var location in folder.Locations)
                    {
                        if (!string.IsNullOrWhiteSpace(location) && Directory.Exists(location))
                        {
                            return location;
                        }
                    }
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to enumerate virtual folders for {Type}", collectionType);
        }

        return null;
    }

    private static string BuildTitleWithYear(string title) => title;

    private static string StripYear(string value)
    {
        var idx = value.LastIndexOf(" (", StringComparison.Ordinal);
        return idx > 0 ? value[..idx] : value;
    }

    private static string ResolveExtension(string? sourcePath)
    {
        if (!string.IsNullOrWhiteSpace(sourcePath))
        {
            var ext = Path.GetExtension(sourcePath);
            if (!string.IsNullOrWhiteSpace(ext))
            {
                return ext;
            }
        }

        return ".mkv";
    }

    private static string Sanitize(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "Unknown";
        }

        var invalid = Path.GetInvalidFileNameChars();
        var chars = value.Select(c => invalid.Contains(c) ? ' ' : c).ToArray();
        var cleaned = new string(chars).Trim();
        while (cleaned.Contains("  ", StringComparison.Ordinal))
        {
            cleaned = cleaned.Replace("  ", " ", StringComparison.Ordinal);
        }

        return string.IsNullOrWhiteSpace(cleaned) ? "Unknown" : cleaned;
    }
}
