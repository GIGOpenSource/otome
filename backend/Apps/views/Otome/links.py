"""进入游戏和落地页是两条不同的地址。"""
import json
import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings

_GAME_ID = re.compile(r"export const GAME_ID = (\d+)")


def clean_public_url(raw):
    text = str(raw or "").strip()[:500]
    if text and not text.startswith(("http://", "https://")):
        return None
    return text


def same_link(left, right):
    return bool(left and right and left.rstrip("/") == right.rstrip("/"))


def resolve_frontend_url(game):
    """玩家直接打开并游玩的地址。"""
    stored = (getattr(game, "frontend_url", "") or "").strip()
    if stored:
        return stored
    base = (getattr(settings, "OTOME_FRONTEND_BASE", "") or "").strip().rstrip("/")
    if base:
        slug = (game.code or "").strip() or str(game.id)
        return f"{base}/{slug}/"
    return _local_frontend_url(game)


def resolve_landing_url(game, request=None):
    """下载页。留空时用这部游戏自己的落地页，不使用进入游戏的地址。"""
    stored = (getattr(game, "landing_url", "") or "").strip()
    if stored:
        return stored
    path = f"/land/{game.id}/"
    if request is not None:
        return request.build_absolute_uri(path)
    return path


def _local_frontend_url(game):
    matched = [item for item in _local_clients() if item["game_id"] == game.id]
    if not matched:
        return ""
    code = (game.code or "").strip()
    for item in matched:
        if code and item["name"] == code:
            return item["url"]
    return matched[0]["url"]


@lru_cache(maxsize=1)
def _local_clients():
    root = Path(getattr(settings, "BACKEND_ROOT", Path(settings.BASE_DIR))).parent / "frontend"
    folders = []
    client = root / "game-client"
    if client.is_dir():
        folders.append(client)
    games_dir = root / "games"
    if games_dir.is_dir():
        folders.extend(path for path in games_dir.iterdir() if path.is_dir())
    found = []
    for folder in folders:
        game_id = _read_game_id(folder / "src" / "config" / "game.js")
        port = _read_port(folder / "src" / "manifest.json")
        if game_id is None or port is None:
            continue
        found.append({
            "name": folder.name,
            "game_id": game_id,
            "url": f"http://127.0.0.1:{port}/",
        })
    return tuple(found)


def _read_game_id(path):
    if not path.is_file():
        return None
    match = _GAME_ID.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    return int(match.group(1))


def _read_port(path):
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    port = ((data.get("h5") or {}).get("devServer") or {}).get("port")
    try:
        port = int(port)
    except (TypeError, ValueError):
        return None
    if port <= 0:
        return None
    return port
