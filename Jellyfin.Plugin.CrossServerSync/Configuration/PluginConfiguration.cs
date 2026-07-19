using MediaBrowser.Model.Plugins;

namespace Jellyfin.Plugin.CrossServerSync.Configuration;

/// <summary>
/// Which direction media is allowed to flow during a sync run.
/// </summary>
public enum SyncDirection
{
    /// <summary>Pull items that exist on the remote server but are missing locally.</summary>
    PullFromRemote,

    /// <summary>Push items that exist locally but are missing on the remote server.</summary>
    PushToRemote,

    /// <summary>Do both: fill gaps on whichever server is missing the item.</summary>
    Bidirectional
}

/// <summary>
/// Plugin configuration. Persisted by Jellyfin as XML under the plugin data folder.
/// </summary>
public class PluginConfiguration : BasePluginConfiguration
{
    /// <summary>
    /// Base URL of the remote Jellyfin server to sync with,
    /// e.g. <c>http://jellyfin.naha.orosapp.us/</c>.
    /// </summary>
    public string RemoteServerUrl { get; set; } = string.Empty;

    /// <summary>
    /// API key generated on the remote server (Dashboard &gt; API Keys).
    /// Used to read the remote library and to download media files.
    /// </summary>
    public string RemoteApiKey { get; set; } = string.Empty;

    /// <summary>
    /// Optional friendly name for the remote server, shown in the UI.
    /// </summary>
    public string RemoteServerName { get; set; } = "Remote server";

    /// <summary>
    /// Direction media is permitted to move.
    /// </summary>
    public SyncDirection Direction { get; set; } = SyncDirection.PullFromRemote;

    /// <summary>
    /// When true, a missing episode/movie detected during a comparison scan is
    /// queued for transfer automatically. When false, transfers only happen when
    /// the user presses "Sync" in the UI or the scheduled task runs.
    /// </summary>
    public bool AutoSync { get; set; }

    /// <summary>
    /// Gigabytes of free space that must remain on the target drive at all times.
    /// A transfer is skipped if completing it would drop free space below this.
    /// Defaults to 100 GB.
    /// </summary>
    public double ReservedSpaceGb { get; set; } = 100;

    /// <summary>
    /// Maximum number of concurrent file transfers.
    /// </summary>
    public int MaxConcurrentTransfers { get; set; } = 1;

    /// <summary>
    /// When true the plugin never deletes or overwrites an existing file, even if
    /// the filenames differ. Matching is done purely on Jellyfin metadata
    /// (provider IDs / series+season+episode), so a differently named copy of the
    /// same logical item is treated as "already present" and skipped.
    /// This is always enforced; the flag is exposed for clarity in the UI.
    /// </summary>
    public bool NeverOverwrite { get; set; } = true;

    /// <summary>
    /// Optional explicit destination folder for movie transfers. When empty the
    /// plugin resolves the first configured Movies library folder automatically.
    /// </summary>
    public string MovieDestinationPath { get; set; } = string.Empty;

    /// <summary>
    /// Optional explicit destination folder for TV transfers. When empty the
    /// plugin resolves the first configured TV Shows library folder automatically.
    /// </summary>
    public string TvDestinationPath { get; set; } = string.Empty;

    /// <summary>
    /// If true, trigger a targeted library scan after a batch of transfers so the
    /// new files are ingested without a full server rescan.
    /// </summary>
    public bool RefreshLibraryAfterSync { get; set; } = true;
}
