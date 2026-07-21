# Fiber Trainer — Android interactive training app

An offline Android app (phone + tablet) that teaches the L2 fiber-technician
basics and quizzes the technician with multiple-choice questions, instant
feedback, scoring, saved progress, and a randomized final exam.

- **8 lesson modules** (Safety, What Fiber Is, Connectors, TX/RX & Polarity,
  Keep It Clean, Reading Records, Link Is Down, Labeling), each with a short
  plain-English lesson and a 5-question quiz.
- **Final Exam** — 15 mixed questions pulled from every module; 80% to pass.
- Progress and best scores are saved on-device (`localStorage`), fully offline.

## What it is technically
A lightweight WebView app: a native `Activity` (`src/.../MainActivity.java`)
hosts a `WebView` that loads the self-contained web app in `assets/`
(`index.html` + `data.js`). No AndroidX, no Gradle/AGP, no network — so it
builds from the raw SDK tools and runs anywhere from Android 5.0 (API 21) up.

## Build the APK
Requires: JDK, Android SDK with `platforms;android-34`, `build-tools;34.0.0`,
and `build-tools;35.0.0` (its newer `d8` is used because 34's `d8` crashes on
nested classes under JDK 21).

```bash
export ANDROID_HOME=/path/to/android-sdk
bash build.sh
# -> FiberTrainer.apk  (signed, sideloadable)
```

The build runs: `aapt2 compile` → `aapt2 link` (bundles `assets/`, generates
`R.java`) → `javac` → `d8` → add `classes.dex` → `zipalign` → `apksigner`.
It is signed with a local debug keystore (`debug.keystore`, auto-created).

## Install on a device (sideload)
This APK is not from the Play Store, so allow installs from your file manager
/ browser once, then open the APK:

1. Copy `FiberTrainer.apk` to the phone or tablet (USB, Drive, email, etc.).
2. Tap it in the Files app. If prompted, enable **Allow from this source**
   (Settings → Apps → special access → Install unknown apps).
3. Tap **Install**, then open **Fiber Trainer** from your app drawer.

## Editing the course content
All lessons and questions live in `assets/data.js` as plain data
(`{ q, options[], answer, why }`). Edit it and re-run `build.sh`. No Java or
layout changes are needed to add/adjust questions or modules.

Vendor-neutral training aid — always follow your site's own records, safety
rules, and standards.
