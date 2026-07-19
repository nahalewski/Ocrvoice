using Jellyfin.Plugin.CrossServerSync.Configuration;
using Jellyfin.Plugin.CrossServerSync.Sync;
using MediaBrowser.Model.Tasks;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.CrossServerSync.ScheduledTasks;

/// <summary>
/// Scheduled task that periodically compares the two servers and, when
/// auto-sync is enabled, pulls any newly detected missing items.
/// </summary>
public class CrossServerSyncTask : IScheduledTask
{
    private readonly SyncService _syncService;
    private readonly ILogger<CrossServerSyncTask> _logger;

    /// <summary>
    /// Initializes a new instance of the <see cref="CrossServerSyncTask"/> class.
    /// </summary>
    /// <param name="syncService">The sync service.</param>
    /// <param name="logger">Logger.</param>
    public CrossServerSyncTask(SyncService syncService, ILogger<CrossServerSyncTask> logger)
    {
        _syncService = syncService;
        _logger = logger;
    }

    /// <inheritdoc />
    public string Name => "Cross-Server Sync";

    /// <inheritdoc />
    public string Key => "CrossServerSyncTask";

    /// <inheritdoc />
    public string Description =>
        "Compares this server's movie and TV libraries against the configured " +
        "remote Jellyfin server and, when auto-sync is enabled, pulls missing items.";

    /// <inheritdoc />
    public string Category => "Cross-Server Sync";

    /// <inheritdoc />
    public async Task ExecuteAsync(IProgress<double> progress, CancellationToken cancellationToken)
    {
        var config = Plugin.Instance?.Configuration ?? new PluginConfiguration();
        progress.Report(5);

        if (!config.AutoSync)
        {
            // Comparison only, so the UI has fresh data and the log shows the gap.
            var report = await _syncService.CompareAsync(cancellationToken).ConfigureAwait(false);
            progress.Report(100);
            if (report.Error is not null)
            {
                _logger.LogWarning("Scheduled comparison error: {Error}", report.Error);
                return;
            }

            var missingMovies = report.MoviesMissingLocally.Count;
            var missingEpisodes = report.SeriesMissingLocally.Sum(s => s.MissingEpisodeCount);
            _logger.LogInformation(
                "Scheduled comparison complete. Auto-sync off. Missing locally: " +
                "{Movies} movies, {Episodes} episodes.",
                missingMovies,
                missingEpisodes);
            return;
        }

        _logger.LogInformation("Scheduled auto-sync starting.");
        progress.Report(10);
        var result = await _syncService.SyncAllAsync(cancellationToken).ConfigureAwait(false);
        progress.Report(100);

        _logger.LogInformation(
            "Scheduled auto-sync complete. Copied {Copied}, skipped {Skipped}, failed {Failed}. {Message}",
            result.CopiedCount,
            result.SkippedCount,
            result.FailedCount,
            result.Message ?? string.Empty);
    }

    /// <inheritdoc />
    public IEnumerable<TaskTriggerInfo> GetDefaultTriggers()
    {
        // Run every 12 hours by default.
        yield return new TaskTriggerInfo
        {
            Type = TaskTriggerInfo.TriggerInterval,
            IntervalTicks = TimeSpan.FromHours(12).Ticks
        };
    }
}
