using System.Globalization;
using Jellyfin.Plugin.CrossServerSync.Configuration;
using MediaBrowser.Common.Configuration;
using MediaBrowser.Common.Plugins;
using MediaBrowser.Model.Plugins;
using MediaBrowser.Model.Serialization;

namespace Jellyfin.Plugin.CrossServerSync;

/// <summary>
/// Cross-Server Sync plugin entry point.
/// </summary>
public class Plugin : BasePlugin<PluginConfiguration>, IHasWebPages
{
    /// <summary>
    /// Initializes a new instance of the <see cref="Plugin"/> class.
    /// </summary>
    /// <param name="applicationPaths">Server application paths.</param>
    /// <param name="xmlSerializer">XML serializer.</param>
    public Plugin(IApplicationPaths applicationPaths, IXmlSerializer xmlSerializer)
        : base(applicationPaths, xmlSerializer)
    {
        Instance = this;
    }

    /// <summary>
    /// Gets the current plugin instance.
    /// </summary>
    public static Plugin? Instance { get; private set; }

    /// <inheritdoc />
    public override string Name => "Cross-Server Sync";

    /// <inheritdoc />
    public override string Description =>
        "Compares this Jellyfin server's movie and TV libraries against a second " +
        "Jellyfin server using Jellyfin metadata, and fills in missing items " +
        "without overwriting existing files.";

    /// <inheritdoc />
    public override Guid Id => Guid.Parse("b8b5f6a2-3c1e-4e7a-9d2b-2a7f5c9e11d4");

    /// <inheritdoc />
    public IEnumerable<PluginPageInfo> GetPages()
    {
        var prefix = GetType().Namespace;
        return new[]
        {
            new PluginPageInfo
            {
                Name = "CrossServerSync",
                EmbeddedResourcePath = string.Format(
                    CultureInfo.InvariantCulture,
                    "{0}.Configuration.configPage.html",
                    prefix)
            }
        };
    }
}
