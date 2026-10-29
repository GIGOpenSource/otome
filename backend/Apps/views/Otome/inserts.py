"""剧情结束后插入的视频或图片，会同步成一条故事解锁。"""
import logging

from Apps.views.Otome.content_i18n import clean_texts
from models.models import OtomeAsset, OtomeGalleryItem

logger = logging.getLogger(__name__)


def sync_insert_gallery(node):
    """有插入素材时保留一条解锁记录；清空插入时把这条记录收起来。"""
    existing = OtomeGalleryItem.objects.filter(game_id=node.game_id, unlock_node=node, is_insert=True).first()
    asset = node.insert_media if node.insert_media_id and not node.insert_media.is_deleted else None
    if asset is None or asset.asset_type not in (OtomeAsset.TYPE_IMAGE, OtomeAsset.TYPE_VIDEO):
        if existing and not existing.is_deleted:
            existing.is_deleted = True
            existing.save(update_fields=["is_deleted", "updated_at"])
        return None
    if asset.game_id is None:
        asset.game_id = node.game_id
        asset.save(update_fields=["game", "updated_at"])
    kind = OtomeGalleryItem.KIND_VIDEO if asset.asset_type == OtomeAsset.TYPE_VIDEO else OtomeGalleryItem.KIND_PORTRAIT
    title = (node.insert_title or asset.name or "回忆")[:100]
    if existing is None:
        existing = OtomeGalleryItem(game_id=node.game_id, unlock_node=node, is_insert=True)
    existing.kind = kind
    existing.asset = asset
    existing.title = title
    existing.unlocked_by_default = False
    existing.is_insert = True
    existing.is_deleted = False
    existing.sort_order = node.sort_order
    existing.lang = node.lang or "zh-Hans"
    packs = {}
    for code, row in (node.texts or {}).items():
        title = str((row or {}).get("insert_title") or "").strip()
        if title:
            packs[code] = {"title": title[:100]}
    if not node.insert_title and asset is not None:
        for code, row in (asset.texts or {}).items():
            if code in packs:
                continue
            title = str((row or {}).get("name") or "").strip()
            if title:
                packs[code] = {"title": title[:100]}
    try:
        existing.texts = clean_texts(packs, ("title",), {"title": 100}, existing.lang)
    except ValueError:
        existing.texts = {}
    existing.save()
    logger.info("同步剧情插入 node=%s gallery=%s kind=%s", node.id, existing.id, kind)
    return existing
