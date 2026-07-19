namespace Jellyfin.Plugin.CrossServerSync.Models;

/// <summary>Which server holds the authoritative copy of an item.</summary>
public enum ItemSide
{
    /// <summary>The item lives on the local (this) server.</summary>
    Local,

    /// <summary>The item lives on the remote server.</summary>
    Remote
}

/// <summary>The kind of media a gap refers to.</summary>
public enum MediaKind
{
    /// <summary>A movie.</summary>
    Movie,

    /// <summary>A whole missing series.</summary>
    Series,

    /// <summary>A missing episode.</summary>
    Episode
}

/// <summary>
/// A single missing item detected when comparing the two servers.
/// </summary>
public class MissingItem
{
    /// <summary>Gets or sets the kind of media.</summary>
    public MediaKind Kind { get; set; }

    /// <summary>Gets or sets the display title, e.g. "The Wire (2002)".</summary>
    public string Title { get; set; } = string.Empty;

    /// <summary>Gets or sets the parent series title (episodes only).</summary>
    public string? SeriesTitle { get; set; }

    /// <summary>Gets or sets the season number (episodes only).</summary>
    public int? SeasonNumber { get; set; }

    /// <summary>Gets or sets the episode number (episodes only).</summary>
    public int? EpisodeNumber { get; set; }

    /// <summary>Gets or sets the metadata match key.</summary>
    public string MatchKey { get; set; } = string.Empty;

    /// <summary>Gets or sets the item id on the side that has the file.</summary>
    public string SourceItemId { get; set; } = string.Empty;

    /// <summary>Gets or sets which server currently holds the file.</summary>
    public ItemSide Source { get; set; }

    /// <summary>Gets or sets the estimated transfer size in bytes.</summary>
    public long? SizeBytes { get; set; }

    /// <summary>Gets or sets the source file path, for display / logging.</summary>
    public string? SourcePath { get; set; }
}

/// <summary>
/// The full result of comparing local and remote libraries, grouped for the UI.
/// </summary>
public class ComparisonReport
{
    /// <summary>Gets or sets when the comparison ran (UTC).</summary>
    public DateTime GeneratedUtc { get; set; } = DateTime.UtcNow;

    /// <summary>Gets or sets the remote server display name.</summary>
    public string RemoteServerName { get; set; } = string.Empty;

    /// <summary>Gets or sets movies missing on the local server.</summary>
    public List<MissingItem> MoviesMissingLocally { get; set; } = new();

    /// <summary>Gets or sets movies missing on the remote server.</summary>
    public List<MissingItem> MoviesMissingRemotely { get; set; } = new();

    /// <summary>Gets or sets series/episodes missing on the local server, grouped by series.</summary>
    public List<SeriesGap> SeriesMissingLocally { get; set; } = new();

    /// <summary>Gets or sets series/episodes missing on the remote server, grouped by series.</summary>
    public List<SeriesGap> SeriesMissingRemotely { get; set; } = new();

    /// <summary>Gets or sets a human-readable error, if the comparison failed.</summary>
    public string? Error { get; set; }
}

/// <summary>
/// A series that is missing whole seasons or individual episodes on one side.
/// </summary>
public class SeriesGap
{
    /// <summary>Gets or sets the series title.</summary>
    public string SeriesTitle { get; set; } = string.Empty;

    /// <summary>Gets or sets the series match key.</summary>
    public string MatchKey { get; set; } = string.Empty;

    /// <summary>Gets or sets true when the series does not exist at all on the target side.</summary>
    public bool SeriesEntirelyMissing { get; set; }

    /// <summary>Gets or sets the seasons (numbers) that are entirely missing.</summary>
    public List<int> MissingSeasons { get; set; } = new();

    /// <summary>Gets or sets the individual missing episodes.</summary>
    public List<MissingItem> MissingEpisodes { get; set; } = new();

    /// <summary>Gets the count of missing episodes.</summary>
    public int MissingEpisodeCount => MissingEpisodes.Count;
}

/// <summary>Outcome of a single transfer.</summary>
public enum TransferStatus
{
    /// <summary>The file was copied successfully.</summary>
    Copied,

    /// <summary>Skipped because a metadata match already exists on the target.</summary>
    SkippedAlreadyPresent,

    /// <summary>Skipped because copying would breach the reserved free-space floor.</summary>
    SkippedInsufficientSpace,

    /// <summary>Skipped because no valid destination library folder was found.</summary>
    SkippedNoDestination,

    /// <summary>The transfer failed.</summary>
    Failed
}

/// <summary>The result of attempting to transfer one item.</summary>
public class TransferResult
{
    /// <summary>Gets or sets the item that was processed.</summary>
    public MissingItem Item { get; set; } = new();

    /// <summary>Gets or sets the outcome.</summary>
    public TransferStatus Status { get; set; }

    /// <summary>Gets or sets the destination path written to, if any.</summary>
    public string? DestinationPath { get; set; }

    /// <summary>Gets or sets bytes actually written.</summary>
    public long BytesWritten { get; set; }

    /// <summary>Gets or sets an explanatory message.</summary>
    public string? Message { get; set; }
}

/// <summary>Summary of a sync run, returned to the UI and logged.</summary>
public class SyncRunResult
{
    /// <summary>Gets or sets when the run started (UTC).</summary>
    public DateTime StartedUtc { get; set; } = DateTime.UtcNow;

    /// <summary>Gets or sets the per-item results.</summary>
    public List<TransferResult> Results { get; set; } = new();

    /// <summary>Gets the number of files copied.</summary>
    public int CopiedCount => Results.Count(r => r.Status == TransferStatus.Copied);

    /// <summary>Gets the number of items skipped.</summary>
    public int SkippedCount => Results.Count(r =>
        r.Status is TransferStatus.SkippedAlreadyPresent
            or TransferStatus.SkippedInsufficientSpace
            or TransferStatus.SkippedNoDestination);

    /// <summary>Gets the number of failures.</summary>
    public int FailedCount => Results.Count(r => r.Status == TransferStatus.Failed);

    /// <summary>Gets the total bytes written.</summary>
    public long TotalBytesWritten => Results.Sum(r => r.BytesWritten);

    /// <summary>Gets or sets a top-level message (e.g. why the run aborted).</summary>
    public string? Message { get; set; }
}
