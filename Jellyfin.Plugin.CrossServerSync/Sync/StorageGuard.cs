using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.CrossServerSync.Sync;

/// <summary>
/// Enforces the "leave N GB free" rule. Before every transfer it checks the
/// drive that hosts the destination folder and refuses the copy if completing it
/// would drop free space below the reserved floor.
/// </summary>
public class StorageGuard
{
    private readonly long _reservedBytes;
    private readonly ILogger _logger;

    /// <summary>
    /// Initializes a new instance of the <see cref="StorageGuard"/> class.
    /// </summary>
    /// <param name="reservedGb">Gigabytes to keep free on the target drive.</param>
    /// <param name="logger">Logger.</param>
    public StorageGuard(double reservedGb, ILogger logger)
    {
        _reservedBytes = (long)Math.Max(0, reservedGb) * 1024L * 1024L * 1024L;
        _logger = logger;
    }

    /// <summary>Gets the reserved space in bytes.</summary>
    public long ReservedBytes => _reservedBytes;

    /// <summary>
    /// Returns the free bytes on the drive hosting <paramref name="path"/>,
    /// or null if it cannot be determined.
    /// </summary>
    /// <param name="path">Any path on the target drive (need not exist yet).</param>
    /// <returns>Free bytes, or null.</returns>
    public long? GetAvailableBytes(string path)
    {
        try
        {
            var root = FindExistingRoot(path);
            if (root is null)
            {
                return null;
            }

            var drive = new DriveInfo(Path.GetPathRoot(root) ?? root);
            return drive.AvailableFreeSpace;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Could not determine free space for {Path}", path);
            return null;
        }
    }

    /// <summary>
    /// Checks whether a file of <paramref name="incomingBytes"/> can be written to
    /// <paramref name="destinationPath"/> while keeping the reserved floor intact.
    /// </summary>
    /// <param name="destinationPath">Intended destination path.</param>
    /// <param name="incomingBytes">Size of the incoming file (0 if unknown).</param>
    /// <returns>True when the copy is allowed.</returns>
    public bool CanFit(string destinationPath, long incomingBytes)
    {
        var available = GetAvailableBytes(destinationPath);
        if (available is null)
        {
            // Fail closed: if we cannot measure the drive, do not risk filling it.
            _logger.LogWarning(
                "Free space for {Path} is unknown; refusing transfer to stay safe.",
                destinationPath);
            return false;
        }

        var remainingAfter = available.Value - Math.Max(0, incomingBytes);
        var allowed = remainingAfter >= _reservedBytes;
        if (!allowed)
        {
            _logger.LogInformation(
                "Skipping transfer to {Path}: {Available} free, need {Incoming} for file and " +
                "must keep {Reserved} free.",
                destinationPath,
                Format(available.Value),
                Format(incomingBytes),
                Format(_reservedBytes));
        }

        return allowed;
    }

    private static string? FindExistingRoot(string path)
    {
        var current = Path.GetFullPath(path);
        while (!string.IsNullOrEmpty(current))
        {
            if (Directory.Exists(current))
            {
                return current;
            }

            var parent = Path.GetDirectoryName(current);
            if (string.IsNullOrEmpty(parent) || parent == current)
            {
                return null;
            }

            current = parent;
        }

        return null;
    }

    private static string Format(long bytes)
    {
        string[] units = { "B", "KB", "MB", "GB", "TB" };
        double value = bytes;
        var unit = 0;
        while (value >= 1024 && unit < units.Length - 1)
        {
            value /= 1024;
            unit++;
        }

        return $"{value:0.##} {units[unit]}";
    }
}
