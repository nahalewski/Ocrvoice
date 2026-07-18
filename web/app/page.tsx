"use client";

import { useEffect, useRef, useState } from "react";
import type { Worker } from "tesseract.js";

type Status = "idle" | "loading" | "ready" | "scanning" | "error";
type CaptureMode = "screen" | "camera" | null;
const ROI = { left: .29, top: .76, right: .75, bottom: .95 };
const MENU_WORDS = new Set(["log", "options", "save", "load", "inventory", "map", "system", "adventure log", "continue", "cancel", "confirm", "back"]);

function cleanText(raw: string) {
  return raw.replace(/\|/g, "I").replace(/[^A-Za-z0-9.,!?;:'"…\-\s]/g, " ").replace(/\s+/g, " ").replace(/^[ .-_\"]+|[ .-_\"]+$/g, "").trim();
}
function looksLikeDialogue(text: string) {
  const normalized = text.toLowerCase().replace(/[.!?;:]/g, "").trim();
  const words = text.match(/[A-Za-z']+/g) ?? [];
  const letters = [...text].filter((char) => /[A-Za-z]/.test(char)).length;
  return !MENU_WORDS.has(normalized) && words.length >= 3 && text.length >= 12 && letters / Math.max(text.length, 1) >= .55;
}

export default function Home() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const cropRef = useRef<HTMLCanvasElement>(null);
  const workerRef = useRef<Worker | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastCandidate = useRef("");
  const candidateCount = useRef(0);
  const lastSpoken = useRef("");
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("Choose the OBS preview or game window to begin.");
  const [dialogue, setDialogue] = useState("Waiting for dialogue…");
  const [history, setHistory] = useState<string[]>([]);
  const [voiceName, setVoiceName] = useState("");
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [rate, setRate] = useState(1);
  const [muted, setMuted] = useState(false);
  const [showCrop, setShowCrop] = useState(true);
  const [captureMode, setCaptureMode] = useState<CaptureMode>(null);

  useEffect(() => {
    const refreshVoices = () => {
      const list = window.speechSynthesis.getVoices();
      voicesRef.current = list; setVoices(list);
      if (!voiceName && list.length) setVoiceName((list.find((v) => v.lang.startsWith("en")) ?? list[0]).name);
    };
    refreshVoices(); window.speechSynthesis.addEventListener("voiceschanged", refreshVoices);
    return () => { window.speechSynthesis.removeEventListener("voiceschanged", refreshVoices); stop(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function speak(text: string) {
    if (muted) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = rate; utterance.pitch = .86; utterance.volume = 1;
    utterance.voice = voicesRef.current.find((v) => v.name === voiceName) ?? null;
    window.speechSynthesis.speak(utterance);
  }
  async function ensureWorker() {
    if (workerRef.current) return workerRef.current;
    setStatus("loading"); setMessage("Loading the on-device dialogue reader…");
    // Tesseract relies on browser worker APIs. Loading it lazily prevents the
    // package's Node entry point from being evaluated by Render during SSR.
    const { createWorker } = await import("tesseract.js");
    const worker = await createWorker("eng", 1, { logger: (event) => {
      if (event.status === "recognizing text") setMessage(`Reading dialogue… ${Math.round(event.progress * 100)}%`);
    }});
    await worker.setParameters({ tessedit_pageseg_mode: "6" as never, preserve_interword_spaces: "1" });
    workerRef.current = worker; return worker;
  }
  function drawCrop() {
    const video = videoRef.current, canvas = cropRef.current;
    if (!video || !canvas || !video.videoWidth) return null;
    const sx = video.videoWidth * ROI.left, sy = video.videoHeight * ROI.top;
    const sw = video.videoWidth * (ROI.right - ROI.left), sh = video.videoHeight * (ROI.bottom - ROI.top);
    canvas.width = Math.round(sw * 2); canvas.height = Math.round(sh * 2);
    const context = canvas.getContext("2d", { willReadFrequently: true }); if (!context) return null;
    context.drawImage(video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data; let dark = 0;
    for (let i = 0; i < pixels.length; i += 16) if (pixels[i] * .21 + pixels[i + 1] * .72 + pixels[i + 2] * .07 < 105) dark++;
    context.filter = "contrast(180%) grayscale(100%)"; context.drawImage(canvas, 0, 0); context.filter = "none";
    return dark / (pixels.length / 16);
  }
  async function scan() {
    if (!streamRef.current?.active) return;
    try {
      const darkRatio = drawCrop();
      if (darkRatio !== null && darkRatio >= .24 && cropRef.current) {
        const result = await (await ensureWorker()).recognize(cropRef.current);
        const text = cleanText(result.data.text), normalized = text.toLowerCase().replace(/\W+/g, " ").trim();
        if (looksLikeDialogue(text)) {
          if (normalized === lastCandidate.current) candidateCount.current++; else { lastCandidate.current = normalized; candidateCount.current = 1; }
          setDialogue(text);
          if (candidateCount.current >= 2 && normalized !== lastSpoken.current) {
            lastSpoken.current = normalized; setHistory((items) => [text, ...items].slice(0, 6)); speak(text);
          }
        } else { lastCandidate.current = ""; candidateCount.current = 0; }
      }
      setStatus("scanning"); setMessage("Live scanning—the game stays on this device.");
    } catch (error) { console.error(error); setStatus("error"); setMessage("The reader hit a problem. Stop and share the window again."); return; }
    timerRef.current = setTimeout(scan, 650);
  }
  async function attachStream(stream: MediaStream, mode: Exclude<CaptureMode, null>) {
    streamRef.current = stream; setCaptureMode(mode);
    if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play(); }
    stream.getVideoTracks()[0].addEventListener("ended", stop);
    setStatus("ready");
    setMessage(mode === "camera" ? "Rear camera connected. Aim the scan box at the TV dialogue." : "Screen connected. Watching the dialogue area…");
    scan();
  }
  async function startScreen() {
    if (!navigator.mediaDevices?.getDisplayMedia) { setStatus("error"); setMessage("Screen sharing is not supported here. Use current Chrome or Edge."); return; }
    try {
      await ensureWorker();
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: { ideal: 12, max: 20 } }, audio: false });
      await attachStream(stream, "screen");
    } catch (error) { if ((error as DOMException).name !== "NotAllowedError") console.error(error); setStatus("idle"); setMessage("Screen sharing was canceled. Choose the OBS preview when ready."); }
  }
  async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) { setStatus("error"); setMessage("Camera access is not supported in this browser."); return; }
    try {
      await ensureWorker();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 12, max: 20 } },
        audio: false,
      });
      await attachStream(stream, "camera");
    } catch (error) {
      if ((error as DOMException).name !== "NotAllowedError") console.error(error);
      setStatus("idle"); setMessage("Camera access was canceled. Allow the rear camera to scan a TV.");
    }
  }
  function stop() {
    if (timerRef.current) clearTimeout(timerRef.current);
    streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    window.speechSynthesis.cancel(); setStatus("idle"); setCaptureMode(null); setMessage("Reader stopped. Camera and screen sharing are off.");
  }
  const isRunning = status === "ready" || status === "scanning";

  return <main>
    <header className="topbar"><a className="brand" href="#top"><span className="brandMark">DL</span><span>Dialogue Lantern</span></a><div className={`status ${isRunning ? "active" : ""}`}><span />{isRunning ? "Live" : status === "loading" ? "Loading" : "Offline"}</div></header>
    <section className="hero" id="top"><div className="eyebrow">LIVE GAME ACCESSIBILITY</div><h1>Let every line<br />find its voice.</h1><p className="lede">Share your OBS preview, or point a phone or tablet at the TV. Dialogue Lantern finds Zelda-style dialogue, ignores menus, and reads new lines aloud using voices already on your device.</p><div className="actions">{isRunning ? <button className="primary" onClick={stop}>Stop reading</button> : <><button className="primary" onClick={startScreen} disabled={status === "loading"}>{status === "loading" ? "Loading reader…" : "Share screen"}</button><button className="cameraButton" onClick={startCamera} disabled={status === "loading"}>Use rear camera</button></>}<span className="privacy">No video is uploaded or saved</span></div></section>
    <section className="workspace">
      <div className="viewerPanel"><div className="panelHeader"><div><span className="step">01</span><h2>{captureMode === "camera" ? "TV camera view" : "Screen preview"}</h2></div><label className="switchLabel"><input type="checkbox" checked={showCrop} onChange={(e) => setShowCrop(e.target.checked)} /><span className="switch" />Show scan area</label></div><div className="viewer"><video ref={videoRef} muted playsInline autoPlay />{showCrop && <div className="scanArea"><span>Align dialogue here</span></div>}{!isRunning && <div className="emptyState"><div className="frameIcon" /><strong>No video connected</strong><p>Share an OBS/game window, or use the rear camera and aim it at your TV.</p></div>}</div><canvas ref={cropRef} className="hiddenCanvas" /><p className="systemMessage"><span className={`dot ${isRunning ? "on" : ""}`} />{message}</p></div>
      <aside className="controlPanel"><div className="panelHeader"><div><span className="step">02</span><h2>Voice & reading</h2></div></div><label className="fieldLabel" htmlFor="voice">Device voice</label><select id="voice" value={voiceName} onChange={(e) => setVoiceName(e.target.value)}>{voices.map((voice) => <option key={`${voice.name}-${voice.lang}`} value={voice.name}>{voice.name} · {voice.lang}</option>)}</select><div className="rangeRow"><label htmlFor="rate">Reading speed</label><output>{rate.toFixed(1)}×</output></div><input id="rate" type="range" min="0.6" max="1.5" step="0.1" value={rate} onChange={(e) => setRate(Number(e.target.value))} /><button className="secondary" onClick={() => speak("The dialogue reader is ready.")}>Test voice</button><label className="mute"><input type="checkbox" checked={muted} onChange={(e) => setMuted(e.target.checked)} />Mute spoken dialogue</label><div className="note"><strong>Browser voice</strong><p>This version uses speech built into your browser and operating system. It does not use ElevenLabs.</p></div></aside>
    </section>
    <section className="transcript"><div className="transcriptLead"><span className="step">03</span><div><h2>Detected dialogue</h2><p>The same line must appear twice before it is spoken, preventing flicker and repeats.</p></div></div><blockquote>{dialogue}</blockquote>{history.length > 1 && <div className="history">{history.slice(1).map((line, i) => <p key={`${line}-${i}`}>{line}</p>)}</div>}</section>
    <footer><span>Best with a 16:9 Tears of the Kingdom picture.</span><span>Rear camera works on iPhone, iPad, and Android.</span></footer>
  </main>;
}
