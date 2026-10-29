#!/usr/bin/env python3
"""复制一份只负责播放的客户端，并写入后台的游戏 ID。"""
import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "game-client"


def main():
    parser = argparse.ArgumentParser(description="按游戏 ID 复制播放客户端")
    parser.add_argument("--game-id", type=int, required=True)
    parser.add_argument("--name", required=True, help="目录名，例如 starry-night")
    parser.add_argument("--title", default="", help="客户端显示名")
    parser.add_argument("--port", type=int, default=0, help="H5 端口，每部游戏各用一个")
    args = parser.parse_args()
    dest = ROOT / "frontend" / "games" / args.name
    if dest.exists():
        raise SystemExit(f"目录已存在：{dest}")
    shutil.copytree(
        SRC,
        dest,
        ignore=shutil.ignore_patterns("node_modules", "unpackage", "dist"),
    )
    config = (dest / "src" / "config" / "game.js").read_text(encoding="utf-8")
    config = re.sub(r"export const GAME_ID = \d+", f"export const GAME_ID = {args.game_id}", config)
    if args.title:
        config = re.sub(r'export const APP_NAME = ".*"', f'export const APP_NAME = "{args.title}"', config)
    (dest / "src" / "config" / "game.js").write_text(config, encoding="utf-8")
    if args.title:
        for relative in ("src/manifest.json", "src/pages.json"):
            path = dest / relative
            path.write_text(path.read_text(encoding="utf-8").replace("星河剧场", args.title), encoding="utf-8")
    if args.port:
        manifest = dest / "src" / "manifest.json"
        text = manifest.read_text(encoding="utf-8")
        text = re.sub(r'"port":\s*\d+', f'"port": {args.port}', text, count=1)
        text = text.replace("__UNI__OTOME0001", f"__UNI__OTOME{args.game_id:04d}")
        manifest.write_text(text, encoding="utf-8")
    print(dest)
    print(f"GAME_ID = {args.game_id}")
    print("进入该目录后执行 npm install && npm run dev:h5")


if __name__ == "__main__":
    main()
