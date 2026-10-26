#!/usr/bin/env bash
# Packages dist/PandorasBoxRemaster/ (PyInstaller onedir) as an AppImage for distros
# without .deb support. Needs appimagetool (APPIMAGETOOL=path, else downloaded).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUNDLE="$ROOT/dist/PandorasBoxRemaster"
VERSION="$(grep -o '__version__ = "[^"]*"' "$ROOT/src/pbremaster/__init__.py" | cut -d'"' -f2)"
APPDIR="$ROOT/dist/AppDir"
OUT="$ROOT/dist/PandorasBoxRemaster-${VERSION}-x86_64.AppImage"

[ -d "$BUNDLE" ] || { echo "error: $BUNDLE not found, run PyInstaller first" >&2; exit 1; }

TOOL="${APPIMAGETOOL:-$ROOT/dist/appimagetool}"
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi

rm -rf "$APPDIR" "$OUT"
mkdir -p "$APPDIR/usr/lib/pandoras-box-remaster"
cp -R "$BUNDLE"/. "$APPDIR/usr/lib/pandoras-box-remaster/"
sed 's|^Exec=.*|Exec=PandorasBoxRemaster|' "$ROOT/packaging/linux/pandoras-box-remaster.desktop" \
  > "$APPDIR/pandoras-box-remaster.desktop"
cp "$ROOT/packaging/icons/icon_256.png" "$APPDIR/pandoras-box-remaster.png"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/pandoras-box-remaster/PandorasBoxRemaster" "$@"
RUN
chmod +x "$APPDIR/AppRun"

ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" "$APPDIR" "$OUT"
rm -rf "$APPDIR"
echo "wrote $OUT"
