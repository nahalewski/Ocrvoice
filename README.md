# Jellyfin Cross-Server Sync

A Jellyfin plugin that keeps the **Movies** and **TV Shows** libraries of two
Jellyfin servers in step by comparing them on **Jellyfin metadata** — provider
IDs (TMDB / TVDB / IMDB) and season/episode numbers — rather than on file names.
It fills in what a server is missing **without ever overwriting existing files**,
even when the two servers store the same title under different file names.

Built for syncing between:

- `http://UHF.orosapp.us/`
- `http://jellyfin.naha.orosapp.us/`

…but it works with any two Jellyfin servers.

## What it does

- **Metadata-based matching, not filename matching.** Two copies of *The Wire
  (2002) S01E01* match even if one file is `the.wire.s01e01.mkv` and the other is
  `The Wire - 1x01 - The Target.mkv`. Matching uses provider IDs first, falling
  back to normalized title + year.
- **No overwriting.** If a logical item already exists on the target (by
  metadata) or a file already exists at the destination path, it is left
  untouched. This is always enforced.
- **Folder-structure aware.** Pulled files land where Jellyfin's scanner expects
  them:
  - Movies → `Movie Name (Year)/Movie Name (Year).ext`
  - Episodes → `Series Name (Year)/Season NN/Series Name - S01E02 - Title.ext`
- **Storage-aware with a free-space floor.** Before every transfer the plugin
  checks the drive hosting the destination and **refuses to copy if doing so
  would drop free space below a reserved floor (default 100 GB)**. It also
  re-checks mid-copy for streams of unknown length and rolls back a partial file
  if the floor is reached.
- **Dashboard UI.** A plugin page lists, for the server you're on, which movies
  are missing and which shows are missing whole **seasons** or individual
  **episodes** compared to the other server — and lets you pull them per-item,
  per-show, or all at once.
- **Auto-sync.** Optionally pull an item automatically as soon as a scheduled
  comparison detects it is missing.
- **Scheduled task.** Runs every 12 hours by default to refresh the comparison
  and (when auto-sync is on) pull new gaps.

## Direction of transfer

A Jellyfin plugin can only write files to the disks of the server it runs on, so
transfers always **pull** to the local server. To keep **both** servers full,
install this plugin on **each** server and point each one at the other:

| Server | Remote URL it points at |
| ------ | ----------------------- |
| `UHF.orosapp.us` | `http://jellyfin.naha.orosapp.us/` |
| `jellyfin.naha.orosapp.us` | `http://UHF.orosapp.us/` |

The comparison view still shows what the *other* server is missing (report only)
so you always have the full picture from either side.

## Installation

### Build from source

Requires the .NET 8 SDK.

```bash
dotnet publish Jellyfin.Plugin.CrossServerSync/Jellyfin.Plugin.CrossServerSync.csproj \
  -c Release -o publish
```

Copy `publish/Jellyfin.Plugin.CrossServerSync.dll` into a folder named
`CrossServerSync` under your Jellyfin server's `plugins` directory, e.g.:

```
/var/lib/jellyfin/plugins/CrossServerSync/Jellyfin.Plugin.CrossServerSync.dll
```

Restart Jellyfin. The plugin appears under **Dashboard → Plugins → Cross-Server
Sync**.

## Configuration

Open **Dashboard → Plugins → Cross-Server Sync** and set:

| Field | Meaning |
| ----- | ------- |
| Remote server URL | The other Jellyfin server, e.g. `http://jellyfin.naha.orosapp.us/` |
| Remote API key | Create it on the remote server under **Dashboard → API Keys** |
| Sync direction | Pull here / report the remote's gaps / both |
| Keep free on target drive (GB) | Free-space floor, default **100** |
| Movie / TV destination folder | Optional overrides; auto-detected from your libraries otherwise |
| Automatically pull missing items | Enables auto-sync on the scheduled task |

Use **Test connection** to confirm the URL and key, then **Compare with remote
now** to see the gaps.

## How matching works

1. **Movies** — match on `Tmdb` → `Imdb` provider IDs, else normalized
   `title + year`.
2. **Series** — match on `Tvdb` → `Tmdb` → `Imdb`, else normalized
   `title + year`.
3. **Episodes** — matched within a matched series on **season number + episode
   number**.

Because matching is metadata-first, differently named files for the same logical
item are correctly treated as "already present" and skipped.

## Notes & suggestions

- **Run it on both servers** (see *Direction of transfer*) for a true two-way
  sync.
- **API keys** are stored in the plugin configuration on each server; use
  dedicated keys you can revoke.
- **Free-space floor** applies per drive. If your Movies and TV libraries live on
  different drives, each is checked independently against the same floor.
- The plugin does not transcode; it copies the original file (`/Items/{id}/Download`)
  byte-for-byte, so the pulled copy is identical to the source.
- Subtitles/extra files that live *outside* the main media file are not pulled in
  this version — a good candidate for a future enhancement.

## Project layout

```
Jellyfin.Plugin.CrossServerSync/
├── Plugin.cs                      # Plugin entry point + config page registration
├── PluginServiceRegistrator.cs    # DI registration
├── Configuration/                 # Config model + dashboard UI (configPage.html)
├── Models/                        # Media + sync/report models, metadata match keys
├── Remote/RemoteJellyfinClient.cs # REST client for the second server
├── Sync/                          # Local reader, comparer, destination resolver,
│                                  #   storage guard, sync orchestrator
├── Api/                           # Dashboard REST endpoints
└── ScheduledTasks/                # Periodic compare / auto-sync task
```
