"""Update checking against the GitHub Releases feed, as in the other Simple-* apps.

check_for_update() only ever reports a newer release; nothing is downloaded or
installed until the player clicks Update (download_asset + launch_installer).
Never raises on network trouble: offline or rate-limited just means "no update".
"""
from __future__ import annotations

import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

OWNER, REPO = "mikehellyer", "PandorasBoxRemaster"
API_TIMEOUT = 4
DOWNLOAD_TIMEOUT = 60


def _ssl_context():
    # A frozen app can carry the build machine's CA path; certifi's bundle travels with it.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


@dataclass
class UpdateInfo:
    version: str
    url: str
    assets: list[tuple[str, str]]          # (file name, download url)


def _version(tag: str) -> tuple[int, ...]:
    out = []
    for piece in tag.lstrip("vV").split("."):
        digits = "".join(c for c in piece if c.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def is_newer(remote: str, current: str) -> bool:
    return _version(remote) > _version(current)


def check_for_update(current: str, owner: str = OWNER, repo: str = REPO) -> UpdateInfo | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "PandorasBoxRemaster"})
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT, context=_ssl_context()) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    tag = data.get("tag_name")
    if not tag or not is_newer(tag, current):
        return None
    assets = [(a["name"], a["browser_download_url"]) for a in data.get("assets", [])
              if "name" in a and "browser_download_url" in a]
    return UpdateInfo(tag, data.get("html_url", ""), assets)


def running_appimage() -> Path | None:
    p = os.environ.get("APPIMAGE")
    return Path(p) if p else None


def asset_for_this_platform(assets: list[tuple[str, str]]) -> str | None:
    if sys.platform == "win32":
        suffix = ".exe"
    elif running_appimage():
        suffix = ".appimage"
    else:
        suffix = ".deb"
    return next((u for name, u in assets if name.lower().endswith(suffix)), None)


def download_asset(url: str) -> Path | None:
    dest = Path(tempfile.mkdtemp(prefix="pbremaster-update-")) / (url.rsplit("/", 1)[-1] or "update")
    req = urllib.request.Request(url, headers={"User-Agent": "PandorasBoxRemaster"})
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT, context=_ssl_context()) as r, \
                open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
    except OSError:
        return None
    return dest


def launch_installer(path: Path) -> subprocess.Popen | None:
    """Hand the download to the system: run the Windows installer, swap an AppImage
    in place, or install the .deb with apt (via pkexec, one password prompt; plain
    xdg-open can offer 'Uninstall' for an installed package). Raises OSError if nothing
    could be started. Returns the process to wait for on Linux, else None."""
    if sys.platform == "win32":
        os.startfile(str(path))                 # noqa: the installer closes the old version
        return None
    image = running_appimage()
    if image and str(path).lower().endswith(".appimage"):
        path.chmod(0o755)
        shutil.move(str(path), str(image))      # takes effect on the next start
        return None
    pkexec, apt = shutil.which("pkexec"), shutil.which("apt")
    if pkexec and apt:
        return subprocess.Popen([pkexec, apt, "install", "-y", str(path)], stderr=subprocess.PIPE, text=True)
    return subprocess.Popen(["xdg-open", str(path)])
