# Dialogue Lantern web app

A private, browser-based live dialogue reader designed for a 16:9 OBS preview
of *The Legend of Zelda: Tears of the Kingdom*.

## How it works

- The user explicitly shares the OBS preview or game window.
- Tesseract.js scans only the bottom-center dialogue region.
- A dark-panel check and dialogue-length rules reject menus and HUD labels.
- A line must be recognized twice before it is spoken or added to history.
- Web Speech synthesis uses a voice installed in the browser or operating
  system. There is no ElevenLabs integration and screen frames are not sent to
  this app's server.

## Run locally

```sh
npm install
npm run dev
```

Screen sharing requires HTTPS when hosted, or localhost in development. Chrome
and Edge provide the most predictable desktop behavior.

## Deploy on Render

The repository-level `render.yaml` configures a Render Blueprint. Connect the
repository in Render and create the Blueprint; Render uses `web` as the service
root. No API keys or persistent storage are required.
