#!/usr/bin/env bash
# Build a signed, sideloadable APK with no Gradle/AGP — just the raw SDK tools.
set -euo pipefail

export ANDROID_HOME=${ANDROID_HOME:-/opt/android-sdk}
BT="$ANDROID_HOME/build-tools/34.0.0"
# d8 in build-tools 34 (8.2.2) crashes on nested classes under JDK 21; use 35's d8.
DEXBT="$ANDROID_HOME/build-tools/35.0.0"
PLATFORM="$ANDROID_HOME/platforms/android-34/android.jar"
PROJ="$(cd "$(dirname "$0")" && pwd)"
OUT="$PROJ/build"
PKG="com.dcops.fibertrainer"

rm -rf "$OUT"; mkdir -p "$OUT/compiled_res" "$OUT/gen" "$OUT/classes"

echo "[1/7] compile resources"
"$BT/aapt2" compile --dir "$PROJ/res" -o "$OUT/compiled_res.zip"

echo "[2/7] link resources + manifest (generates R.java)"
"$BT/aapt2" link \
  -o "$OUT/base.apk" \
  -I "$PLATFORM" \
  --manifest "$PROJ/AndroidManifest.xml" \
  -R "$OUT/compiled_res.zip" \
  -A "$PROJ/assets" \
  --java "$OUT/gen" \
  --auto-add-overlay

echo "[3/7] compile Java (R.java + sources)"
find "$OUT/gen" -name "*.java" > "$OUT/srcs.txt"
find "$PROJ/src" -name "*.java" >> "$OUT/srcs.txt"
javac -source 8 -target 8 -bootclasspath "$PLATFORM" \
  -classpath "$PLATFORM" -d "$OUT/classes" @"$OUT/srcs.txt"

echo "[4/7] dex (classes.dex)"
( cd "$OUT/classes" && jar cf "$OUT/classes.jar" . )
"$DEXBT/d8" "$OUT/classes.jar" --lib "$PLATFORM" --min-api 21 --output "$OUT"

echo "[5/7] add classes.dex into apk"
cd "$OUT"
cp base.apk unsigned.apk
"$ANDROID_HOME/build-tools/34.0.0/aapt2" version >/dev/null
# use zip to add the dex at archive root
zip -q -j unsigned.apk classes.dex

echo "[6/7] zipalign"
"$BT/zipalign" -f -p 4 unsigned.apk aligned.apk

echo "[7/7] sign"
KS="$PROJ/debug.keystore"
if [ ! -f "$KS" ]; then
  keytool -genkeypair -v -keystore "$KS" -alias fibertrainer \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass android -keypass android \
    -dname "CN=Fiber Trainer, OU=DC Ops, O=Training, C=US" >/dev/null 2>&1
fi
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
  --out "$PROJ/FiberTrainer.apk" aligned.apk
"$BT/apksigner" verify --print-certs "$PROJ/FiberTrainer.apk" | head -2

echo "DONE -> $PROJ/FiberTrainer.apk"
ls -la "$PROJ/FiberTrainer.apk"
