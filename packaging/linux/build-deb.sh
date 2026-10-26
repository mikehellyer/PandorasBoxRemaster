#!/usr/bin/env bash
# Packages dist/PandorasBoxRemaster/ (PyInstaller onedir) into a .deb that installs to
# /opt/pandoras-box-remaster with a menu entry and icons. Uses dpkg-deb only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUNDLE="$ROOT/dist/PandorasBoxRemaster"
VERSION="$(grep -o '__version__ = "[^"]*"' "$ROOT/src/pbremaster/__init__.py" | cut -d'"' -f2)"
ARCH="$(dpkg --print-architecture)"
STAGE="$ROOT/dist/deb-staging"
OUT="$ROOT/dist/pandoras-box-remaster_${VERSION}_${ARCH}.deb"

[ -d "$BUNDLE" ] || { echo "error: $BUNDLE not found, run PyInstaller first" >&2; exit 1; }

rm -rf "$STAGE" "$OUT"
mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/pandoras-box-remaster" "$STAGE/usr/bin" "$STAGE/usr/share/applications"
cp -R "$BUNDLE"/. "$STAGE/opt/pandoras-box-remaster/"
ln -s /opt/pandoras-box-remaster/PandorasBoxRemaster "$STAGE/usr/bin/pandoras-box-remaster"
cp "$ROOT/packaging/linux/pandoras-box-remaster.desktop" "$STAGE/usr/share/applications/"
for size in 16 32 48 64 128 256 512; do
  dir="$STAGE/usr/share/icons/hicolor/${size}x${size}/apps"
  mkdir -p "$dir"
  cp "$ROOT/packaging/icons/icon_${size}.png" "$dir/pandoras-box-remaster.png"
done

cat > "$STAGE/DEBIAN/control" <<CTRL
Package: pandoras-box-remaster
Version: $VERSION
Section: games
Priority: optional
Architecture: $ARCH
Maintainer: Mike Hellyer
Recommends: zenity
Description: Remaster of Microsoft Pandora's Box (1999)
 Plays the puzzle game on modern Linux using your own copy of the original
 game files (CD or installed copy), which are not included.
CTRL

dpkg-deb --build --root-owner-group "$STAGE" "$OUT"
rm -rf "$STAGE"
echo "wrote $OUT"
