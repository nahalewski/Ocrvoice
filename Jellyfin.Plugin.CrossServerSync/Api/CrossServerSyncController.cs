using Jellyfin.Plugin.CrossServerSync.Configuration;
using Jellyfin.Plugin.CrossServerSync.Models;
using Jellyfin.Plugin.CrossServerSync.Sync;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.CrossServerSync.Api;

/// <summary>
/// REST endpoints backing the plugin's UI. All require an authenticated
/// administrator.
/// </summary>
[ApiController]
[Authorize(Policy = "RequiresElevation")]
[Route("CrossServerSync")]
[Produces("application/json")]
public class CrossServerSyncController : ControllerBase
{
    private readonly SyncService _syncService;
    private readonly ILogger<CrossServerSyncController> _logger;

    /// <summary>
    /// Initializes a new instance of the <see cref="CrossServerSyncController"/> class.
    /// </summary>
    /// <param name="syncService">The sync service.</param>
    /// <param name="logger">Logger.</param>
    public CrossServerSyncController(SyncService syncService, ILogger<CrossServerSyncController> logger)
    {
        _syncService = syncService;
        _logger = logger;
    }

    /// <summary>Returns the current configuration and storage summary.</summary>
    /// <returns>Status payload.</returns>
    [HttpGet("Status")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public ActionResult<object> GetStatus()
    {
        var config = Plugin.Instance?.Configuration ?? new PluginConfiguration();
        return Ok(new
        {
            config.RemoteServerUrl,
            config.RemoteServerName,
            Direction = config.Direction.ToString(),
            config.AutoSync,
            config.ReservedSpaceGb,
            config.NeverOverwrite,
            HasApiKey = !string.IsNullOrWhiteSpace(config.RemoteApiKey)
        });
    }

    /// <summary>Tests the remote connection.</summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>Result of the connection test.</returns>
    [HttpPost("TestConnection")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public async Task<ActionResult<object>> TestConnection(CancellationToken cancellationToken)
    {
        var (success, message) = await _syncService.TestConnectionAsync(cancellationToken).ConfigureAwait(false);
        return Ok(new { success, message });
    }

    /// <summary>
    /// Compares the two servers and returns what each side is missing.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The comparison report.</returns>
    [HttpGet("Compare")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public async Task<ActionResult<ComparisonReport>> Compare(CancellationToken cancellationToken)
    {
        var report = await _syncService.CompareAsync(cancellationToken).ConfigureAwait(false);
        return Ok(report);
    }

    /// <summary>
    /// Runs a full sync (pull everything missing locally that direction allows).
    /// </summary>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The run result.</returns>
    [HttpPost("Sync")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public async Task<ActionResult<SyncRunResult>> Sync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Manual full sync requested via UI.");
        var result = await _syncService.SyncAllAsync(cancellationToken).ConfigureAwait(false);
        return Ok(result);
    }

    /// <summary>
    /// Transfers a specific set of missing items (as returned by Compare).
    /// </summary>
    /// <param name="items">Items to pull.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The run result.</returns>
    [HttpPost("SyncItems")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public async Task<ActionResult<SyncRunResult>> SyncItems(
        [FromBody] List<MissingItem> items,
        CancellationToken cancellationToken)
    {
        if (items is null || items.Count == 0)
        {
            return Ok(new SyncRunResult { Message = "No items supplied." });
        }

        _logger.LogInformation("Targeted sync of {Count} item(s) requested via UI.", items.Count);
        var result = await _syncService.TransferAsync(items, cancellationToken).ConfigureAwait(false);
        return Ok(result);
    }
}
