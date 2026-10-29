import logging

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from models.models import OtomeAsset, OtomeCharacter, OtomeChoice, OtomeGalleryItem, OtomeGame, OtomeNode
from tools.otome_art import (
    render_bgm_hall,
    render_bgm_night,
    render_cover,
    render_dome,
    render_hall,
    render_portrait_gu,
    render_portrait_lu,
    render_roof,
)

logger = logging.getLogger(__name__)

ASSETS = [
    ("cover", "【示例】封面", OtomeAsset.TYPE_IMAGE, "cover.png", render_cover),
    ("bg_roof", "【示例】天台夜色", OtomeAsset.TYPE_IMAGE, "roof.png", render_roof),
    ("bg_dome", "【示例】天文台", OtomeAsset.TYPE_IMAGE, "dome.png", render_dome),
    ("bg_hall", "【示例】礼堂灯下", OtomeAsset.TYPE_IMAGE, "hall.png", render_hall),
    ("portrait_gu", "【示例】顾星河立绘", OtomeAsset.TYPE_IMAGE, "gu.png", render_portrait_gu),
    ("portrait_lu", "【示例】陆沉舟立绘", OtomeAsset.TYPE_IMAGE, "lu.png", render_portrait_lu),
    ("bgm_night", "【示例】夜色配乐", OtomeAsset.TYPE_AUDIO, "night.wav", render_bgm_night),
    ("bgm_hall", "【示例】礼堂配乐", OtomeAsset.TYPE_AUDIO, "hall.wav", render_bgm_hall),
]

CHARACTERS = [
    {
        "key": "gu",
        "name": "顾星河",
        "title": "天文社社长",
        "name_color": "#d7c4ff",
        "portrait": "portrait_gu",
        "intro": "说话很轻。记得每一颗星的名字，却常常把想说的话留在风里。",
        "sort_order": 1,
    },
    {
        "key": "lu",
        "name": "陆沉舟",
        "title": "学生会主席",
        "name_color": "#f0d2a8",
        "portrait": "portrait_lu",
        "intro": "把场面照看得很亮。灯一暗下来，耳朵会先红。",
        "sort_order": 2,
    },
]

NODES = [
    {
        "key": "start",
        "sort": 1,
        "speaker": "旁白",
        "bg": "bg_roof",
        "bgm": "bgm_night",
        "start": True,
        "is_key": True,
        "next": "fork",
        "content": "风从天台边缘翻上来，把一张没有署名的邀请函送到你掌心。纸页上的星图微微发亮，像有人刚用指尖点过。",
    },
    {
        "key": "fork",
        "sort": 2,
        "speaker": "旁白",
        "bg": "bg_roof",
        "bgm": "bgm_night",
        "content": "礼堂的灯在楼下铺开，天文台的圆顶则沉在更暗的夜里。邀请函没有写地点。你得自己选。",
        "choices": [
            ("顺着星图，去天文台", "meet_gu"),
            ("走向灯火，去礼堂", "meet_lu"),
        ],
    },
    {
        "key": "meet_gu",
        "sort": 3,
        "character": "gu",
        "bg": "bg_dome",
        "bgm": "bgm_night",
        "is_key": True,
        "next": "gu_coat",
        "content": "你来了。我还以为，今晚的星星会比人先到。",
    },
    {
        "key": "gu_coat",
        "sort": 4,
        "character": "gu",
        "speaker": "旁白",
        "bg": "bg_dome",
        "bgm": "bgm_night",
        "content": "他看见你指尖发凉，把外套披上来。金属扣轻轻撞了一下你的手腕。他问，冷的话，就站到我这边。",
        "choices": [
            ("把你记得的那颗星说给他听", "gu_end_yes"),
            ("把外套还给他，先不回答", "gu_end_wait"),
        ],
    },
    {
        "key": "gu_end_yes",
        "sort": 5,
        "character": "gu",
        "bg": "bg_dome",
        "bgm": "bgm_night",
        "ending": True,
        "ending_title": "未眠之约",
        "content": "那颗星叫晚星。他重复你的话，笑意很浅。和你一样，总是最后才肯亮。明年的流星雨，我在这里等你。你可以迟到，但要来。",
    },
    {
        "key": "gu_end_wait",
        "sort": 6,
        "character": "gu",
        "speaker": "旁白",
        "bg": "bg_dome",
        "bgm": "bgm_night",
        "ending": True,
        "ending_title": "未说出口",
        "content": "外套回到他臂弯里。他点了点头，像是早就练习过怎么退开一步。没关系。星星会等。我也可以。你走到楼梯口时，听见他在身后把后半句话咽了回去。",
    },
    {
        "key": "meet_lu",
        "sort": 7,
        "character": "lu",
        "bg": "bg_hall",
        "bgm": "bgm_hall",
        "is_key": True,
        "next": "lu_talk",
        "content": "礼堂的灯把一切照得很清楚。他看见你，先把话筒放下了。你真的拆了那封信。",
    },
    {
        "key": "lu_talk",
        "sort": 8,
        "character": "lu",
        "bg": "bg_hall",
        "bgm": "bgm_hall",
        "content": "邀请函是我放的。他顿了顿，耳尖却红了。星图是向天文社借的。如果你现在去找顾星河，就当我没说过。",
        "choices": [
            ("拉他去天台，看真正的星星", "lu_end_roof"),
            ("留在灯下，把这支舞跳完", "lu_end_dance"),
        ],
    },
    {
        "key": "lu_end_roof",
        "sort": 9,
        "character": "lu",
        "bg": "bg_roof",
        "bgm": "bgm_night",
        "ending": True,
        "ending_title": "借来的星图",
        "content": "天台上风很大。他把那张借来的星图按在栏杆上，纸角乱飞。这些我其实大多不认得。所以今晚，可以请你教我吗？从离你名字最近的那颗开始。",
    },
    {
        "key": "lu_end_dance",
        "sort": 10,
        "character": "lu",
        "bg": "bg_hall",
        "bgm": "bgm_hall",
        "ending": True,
        "ending_title": "灯下",
        "content": "曲子还没结束。他向你伸出手，掌心温热，语气却放得很轻。这一支只跳给你。散场以后的路如果还亮着，我就送到宿舍楼下。不亮的话，我也可以先不走。",
    },
]


class Command(BaseCommand):
    help = "写入示例乙游《星河未眠》。已存在时跳过，加 --force 会重做这一部。"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                game = self._build(force=options["force"])
        except Exception:
            logger.error("写入示例乙游失败", exc_info=True)
            raise
        if game is None:
            self.stdout.write(self.style.WARNING("示例故事已存在。要重做请加 --force"))
            return
        self.stdout.write(self.style.SUCCESS(
            f"示例故事《{game.title}》已发布，游戏 ID = {game.id}。客户端 config/game.js 的 GAME_ID 填 {game.id}"
        ))

    def _build(self, force):
        existing = OtomeGame.objects.filter(code="starry-night", is_deleted=False).first()
        if existing and existing.nodes.filter(is_deleted=False).exists() and not force:
            self._attach_assets(existing)
            self._ensure_gallery(existing)
            return None
        assets = {}
        for key, name, asset_type, filename, renderer in ASSETS:
            blob = renderer()
            asset = OtomeAsset.objects.filter(remark=f"seed:{key}").first()
            if asset is None:
                asset = OtomeAsset(remark=f"seed:{key}")
            asset.name = name
            asset.asset_type = asset_type
            asset.url = ""
            asset.is_deleted = False
            if asset.file:
                asset.file.delete(save=False)
            asset.file.save(filename, ContentFile(blob), save=False)
            asset.save()
            assets[key] = asset
            logger.info("示例素材 %s id=%s", key, asset.id)

        game = existing or OtomeGame(code="starry-night")
        game.title = "星河未眠"
        game.subtitle = "天文台的那一夜"
        game.summary = "一张没有署名的邀请函。你要去找星星，还是去找把灯留给你的人。"
        game.cover = assets["cover"]
        game.status = OtomeGame.STATUS_PUBLISHED
        game.is_deleted = False
        game.save()
        if force or existing:
            game.gallery_items.all().delete()
            game.nodes.all().delete()
            game.characters.all().delete()

        characters = {}
        for spec in CHARACTERS:
            character = OtomeCharacter.objects.create(
                game=game,
                name=spec["name"],
                title=spec["title"],
                name_color=spec["name_color"],
                intro=spec["intro"],
                portrait=assets[spec["portrait"]],
                sort_order=spec["sort_order"],
            )
            characters[spec["key"]] = character

        created = {}
        for spec in NODES:
            created[spec["key"]] = OtomeNode.objects.create(
                game=game,
                node_key=spec["key"],
                sort_order=spec["sort"],
                character=characters.get(spec.get("character")),
                speaker_name=spec.get("speaker") or "",
                content=spec["content"],
                background=assets.get(spec.get("bg")),
                bgm=assets.get(spec.get("bgm")),
                is_start=spec.get("start", False),
                is_key=spec.get("is_key", False),
                is_ending=spec.get("ending", False),
                ending_title=spec.get("ending_title") or "",
            )
        for spec in NODES:
            node = created[spec["key"]]
            if spec.get("next"):
                node.next_node = created[spec["next"]]
                node.save(update_fields=["next_node"])
            for index, (text, target) in enumerate(spec.get("choices") or []):
                OtomeChoice.objects.create(
                    node=node,
                    text=text,
                    next_node=created[target],
                    sort_order=index,
                )
        self._attach_assets(game, assets)
        self._ensure_gallery(game)
        return game

    def _attach_assets(self, game, assets=None):
        rows = list(assets.values()) if assets is not None else list(
            OtomeAsset.objects.filter(remark__startswith="seed:", is_deleted=False)
        )
        for asset in rows:
            if asset.game_id != game.id:
                asset.game = game
                asset.save(update_fields=["game", "updated_at"])

    def _ensure_gallery(self, game):
        if game.gallery_items.filter(is_deleted=False).exists():
            return
        by_remark = {
            asset.remark: asset
            for asset in OtomeAsset.objects.filter(remark__startswith="seed:", is_deleted=False)
        }
        nodes = {node.node_key: node for node in game.nodes.filter(is_deleted=False)}
        specs = (
            (OtomeGalleryItem.KIND_PORTRAIT, "seed:portrait_gu", "顾星河", "meet_gu", 1),
            (OtomeGalleryItem.KIND_PORTRAIT, "seed:portrait_lu", "陆沉舟", "meet_lu", 2),
        )
        for kind, remark, title, node_key, sort_order in specs:
            asset = by_remark.get(remark)
            node = nodes.get(node_key)
            if asset is None or node is None:
                continue
            OtomeGalleryItem.objects.create(
                game=game,
                kind=kind,
                asset=asset,
                title=title,
                unlock_node=node,
                sort_order=sort_order,
            )
            logger.info("示例解锁内容 %s", title)
