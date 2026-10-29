"""把专项文件夹里的竖屏、横屏图片挂到《第一夜》和《影中第一》。"""
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from models.models import OtomeAsset, OtomeCharacter, OtomeGalleryItem, OtomeGame, OtomeNode

ROOT = Path.home() / "Desktop" / "专项"
SOURCES = {
    "first-night": ROOT / "男频-人气改编" / "图",
    "shadow-first": ROOT / "女频-人气改编" / "图",
}
FOLDERS = ("背景", "立绘", "封面")


class Command(BaseCommand):
    help = "把专项里的图片写入两部游戏的素材，并分开竖屏和横屏。"

    def handle(self, *args, **options):
        for code, root in SOURCES.items():
            if not root.is_dir():
                raise CommandError(f"找不到图片目录：{root}")
            game = OtomeGame.objects.filter(code=code, is_deleted=False).first()
            if game is None:
                raise CommandError(f"游戏不在库里：{code}")
            attached, missing = attach_game(game, root)
            self.stdout.write(self.style.SUCCESS(f"《{game.title}》挂上 {attached} 张图，缺文件 {missing} 个"))


def attach_game(game, root):
    collects = _collects(root)
    assets = list(OtomeAsset.objects.filter(game=game, is_deleted=False))
    by_name = {item.name: item for item in assets}
    attached = 0
    missing = 0
    for asset in assets:
        if asset.name.endswith("__land"):
            continue
        if asset.asset_type == OtomeAsset.TYPE_VIDEO:
            still = collects.get(asset.name)
            if still is None:
                missing += 1
                continue
            _store(asset, still)
            asset.asset_type = OtomeAsset.TYPE_IMAGE
            asset.save(update_fields=["asset_type", "file", "url", "updated_at"])
            OtomeGalleryItem.objects.filter(game=game, asset=asset, is_deleted=False).update(
                kind=OtomeGalleryItem.KIND_PORTRAIT
            )
            attached += 1
            continue
        if asset.asset_type != OtomeAsset.TYPE_IMAGE:
            continue
        base = asset.name[:-5] if asset.name.endswith("-land") else asset.name
        orient = "横屏" if asset.name.endswith("-land") else "竖屏"
        path = _picture(root, base, orient)
        if path is None:
            missing += 1
            continue
        _store(asset, path)
        asset.screen = OtomeAsset.SCREEN_LANDSCAPE if orient == "横屏" else OtomeAsset.SCREEN_PORTRAIT
        asset.save(update_fields=["screen", "file", "url", "updated_at"])
        attached += 1
        if orient == "横屏" or f"{asset.name}-land" in by_name:
            continue
        land_path = _picture(root, asset.name, "横屏")
        if land_path is None:
            continue
        land = _land_asset(game, asset, by_name)
        _store(land, land_path)
        land.save(update_fields=["file", "url", "updated_at"])
        attached += 1
        _point_landscape(game, asset, land)
    return attached, missing


def _picture(root, name, orient):
    for folder in FOLDERS:
        path = root / folder / orient / f"{name}.png"
        if path.is_file():
            return path
    return None


def _collects(root):
    found = {}
    folder = root / "收藏"
    if not folder.is_dir():
        return found
    for path in folder.iterdir():
        if not path.is_file():
            continue
        key = path.stem.replace("-collect", "")
        if key.endswith("-ear"):
            key = key[:-4] + "-near"
        found[key] = path
    return found


def _land_asset(game, portrait, by_name):
    name = f"{portrait.name}__land"
    land = by_name.get(name)
    if land is None:
        land = OtomeAsset.objects.filter(game=game, name=name, is_deleted=False).first()
    if land is None:
        land = OtomeAsset(
            game=game,
            name=name,
            asset_type=OtomeAsset.TYPE_IMAGE,
            usage=portrait.usage,
            screen=OtomeAsset.SCREEN_LANDSCAPE,
            remark="横屏",
        )
        land.save()
    by_name[name] = land
    return land


def _point_landscape(game, portrait, land):
    OtomeNode.objects.filter(game=game, background_land=portrait).update(background_land=land)
    OtomeNode.objects.filter(game=game, portrait_land=portrait).update(portrait_land=land)
    OtomeCharacter.objects.filter(game=game, portrait_land=portrait).update(portrait_land=land)
    if game.cover_land_id == portrait.id:
        game.cover_land = land
        game.save(update_fields=["cover_land", "updated_at"])


def _store(asset, path):
    if asset.file:
        asset.file.delete(save=False)
    with path.open("rb") as handle:
        asset.file.save(f"{asset.id}-{path.name}", File(handle), save=False)
    asset.url = ""
