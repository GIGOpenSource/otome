from rest_framework import serializers

from models.models import (
    OtomeAsset,
    OtomeCharacter,
    OtomeCharacterImage,
    OtomeChoice,
    OtomeGalleryItem,
    OtomeGame,
    OtomeNode,
    OtomeNodeFigure,
)
from Apps.views.Otome.inserts import sync_insert_gallery
from Apps.views.Otome.landing import clean_ios, clean_package
from Apps.views.Otome.links import clean_public_url, resolve_frontend_url, resolve_landing_url, same_link
from Apps.views.Otome.content_i18n import (
    ASSET_FIELDS,
    ASSET_LIMITS,
    CHARACTER_FIELDS,
    CHARACTER_LIMITS,
    CHOICE_FIELDS,
    CHOICE_LIMITS,
    GALLERY_FIELDS,
    GALLERY_LIMITS,
    GAME_FIELDS,
    GAME_LIMITS,
    IMAGE_FIELDS,
    IMAGE_LIMITS,
    NODE_FIELDS,
    NODE_LIMITS,
    clean_texts,
)
from Apps.views.Otome.i18n import canonical, tr
from Apps.views.Otome.script import resolve_asset_url


def _store_texts(serializer, attrs, fields, limits, source=None):
    initial = serializer.initial_data if isinstance(serializer.initial_data, dict) else {}
    if "texts" not in initial and "texts" not in attrs:
        return attrs
    if source is None:
        source = attrs.get("lang") or getattr(serializer.instance, "lang", None) or "zh-Hans"
    raw = initial.get("texts") if "texts" in initial else attrs.get("texts")
    try:
        attrs["texts"] = clean_texts(raw, fields, limits, source)
    except ValueError:
        raise serializers.ValidationError({"texts": "多语言格式不正确"})
    return attrs


class LangSerializerMixin:
    def validate_lang(self, value):
        if not str(value or "").strip():
            return "zh-Hans"
        code = canonical(value)
        if not code:
            raise serializers.ValidationError("请选择语言")
        return code


def _fmt(template, **kwargs):
    text = tr(template)
    for name, value in kwargs.items():
        text = text.replace("{" + name + "}", tr(value) if isinstance(value, str) else str(value))
    return text


def _reject_deleted(asset, label):
    if asset is not None and asset.is_deleted:
        raise serializers.ValidationError(_fmt("{label}已删除", label=label))


def _ensure_type(asset, expected, label):
    _reject_deleted(asset, label)
    if asset is not None and asset.asset_type != expected:
        kind = "图片" if expected == OtomeAsset.TYPE_IMAGE else "音频"
        raise serializers.ValidationError(_fmt("{label}必须是{kind}", label=label, kind=kind))


class SplashUrlField(serializers.CharField):
    """开屏地址。可以是上传接口返回的网址，也可以是素材编号，保存时写成网址。"""

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_blank", True)
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("max_length", 500)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data is None or data == "":
            return ""
        if isinstance(data, bool):
            self.fail("invalid")
        if isinstance(data, int) or (isinstance(data, str) and data.strip().isdigit()):
            return self._from_asset(int(data))
        text = str(data).strip()
        if text.startswith("/"):
            return text[:500]
        cleaned = clean_public_url(text)
        if cleaned is None:
            raise serializers.ValidationError("开屏封面需要是网址或素材编号")
        return cleaned

    def _from_asset(self, asset_id):
        asset = OtomeAsset.objects.filter(pk=asset_id, is_deleted=False).first()
        if asset is None:
            raise serializers.ValidationError("素材不存在")
        _ensure_visual(asset, "开屏封面")
        url = resolve_asset_url(asset, self.context.get("request"))
        if not url:
            raise serializers.ValidationError("素材没有地址")
        return url[:500]


def _ensure_visual(asset, label):
    _reject_deleted(asset, label)
    if asset is not None and asset.asset_type not in (OtomeAsset.TYPE_IMAGE, OtomeAsset.TYPE_VIDEO):
        raise serializers.ValidationError(_fmt("{label}必须是图片或视频", label=label))


def _screen_size(raw):
    """立绘占画面的百分比。空值或非法值按铺满处理。"""
    try:
        size = int(raw)
    except (TypeError, ValueError):
        return 100
    if size < 1:
        return 1
    if size > 100:
        return 100
    return size


class AssetSerializer(LangSerializerMixin, serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(help_text="客户端可访问的地址")

    class Meta:
        model = OtomeAsset
        fields = [
            "id", "game", "name", "asset_type", "usage", "screen", "url", "file_url",
            "duration", "file_size", "remark", "texts", "lang", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "file_url", "duration", "file_size", "created_at", "updated_at"]
        extra_kwargs = {
            "game": {"required": False, "allow_null": True},
            "name": {"help_text": "素材名称"},
            "asset_type": {"help_text": "image 图片 / audio 音频 / video 视频"},
            "url": {"help_text": "外链。填写后优先于已上传文件", "required": False, "allow_blank": True},
            "usage": {"required": False, "allow_blank": True, "help_text": "background 背景 / character 立绘 / cover 封面"},
            "screen": {"required": False, "allow_blank": True, "help_text": "portrait 竖屏 / landscape 横屏"},
            "remark": {"required": False, "allow_blank": True},
            "lang": {"required": False, "allow_blank": True},
            "texts": {"required": False},
        }

    def validate(self, attrs):
        return _store_texts(self, attrs, ASSET_FIELDS, ASSET_LIMITS)

    def get_file_url(self, obj):
        return resolve_asset_url(obj, self.context.get("request"))

    def update(self, instance, validated_data):
        url = validated_data.get("url")
        if url:
            if instance.file:
                instance.file.delete(save=False)
            instance.file = ""
        return super().update(instance, validated_data)


class GameSerializer(LangSerializerMixin, serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    cover_land_url = serializers.SerializerMethodField()
    splash_url = SplashUrlField()
    splash_land_url = SplashUrlField()
    play_url = serializers.SerializerMethodField()
    landing_page_url = serializers.SerializerMethodField()
    node_count = serializers.SerializerMethodField()

    class Meta:
        model = OtomeGame
        fields = [
            "id", "code", "title", "subtitle", "summary", "texts", "cover", "cover_url",
            "cover_land", "cover_land_url", "splash_url", "splash_land_url", "play_package", "ios_app_id",
            "frontend_url", "play_url", "landing_url", "landing_page_url",
            "status", "lang", "node_count", "sort_order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "cover_url", "cover_land_url", "play_url", "landing_page_url", "node_count", "created_at", "updated_at"]
        extra_kwargs = {
            "code": {"required": False, "allow_null": True, "allow_blank": True, "help_text": "可选编码"},
            "title": {"help_text": "游戏标题"},
            "subtitle": {"required": False, "allow_blank": True},
            "summary": {"required": False, "allow_blank": True},
            "play_package": {"required": False, "allow_blank": True},
            "ios_app_id": {"required": False, "allow_blank": True},
            "frontend_url": {"required": False, "allow_blank": True, "help_text": "进入游戏。玩家直接打开并游玩，留空则用本机客户端"},
            "landing_url": {"required": False, "allow_blank": True, "help_text": "落地页。下载页，和进入游戏不是同一个链接"},
            "cover": {"required": False, "allow_null": True, "help_text": "竖屏封面，1080×1920"},
            "cover_land": {"required": False, "allow_null": True, "help_text": "横屏封面，1920×1080"},
            "splash_url": {"help_text": "开屏竖屏。上传后的网址，或素材编号"},
            "splash_land_url": {"help_text": "开屏横屏。上传后的网址，或素材编号"},
            "status": {"help_text": "0 草稿，1 已发布"},
            "lang": {"required": False, "allow_blank": True},
            "texts": {"required": False},
        }

    def get_cover_url(self, obj):
        return resolve_asset_url(obj.cover, self.context.get("request"))

    def get_cover_land_url(self, obj):
        return resolve_asset_url(obj.cover_land, self.context.get("request"))

    def get_play_url(self, obj):
        return resolve_frontend_url(obj)

    def get_landing_page_url(self, obj):
        return resolve_landing_url(obj, self.context.get("request"))

    def get_node_count(self, obj):
        counted = getattr(obj, "node_count", None)
        if counted is not None:
            return counted
        return obj.nodes.filter(is_deleted=False).count()

    def validate_frontend_url(self, value):
        text = clean_public_url(value)
        if text is None:
            raise serializers.ValidationError("进入游戏的链接需要以 http:// 或 https:// 开头")
        return text

    def validate_landing_url(self, value):
        text = clean_public_url(value)
        if text is None:
            raise serializers.ValidationError("落地页链接需要以 http:// 或 https:// 开头")
        return text

    def validate(self, attrs):
        frontend = attrs.get("frontend_url", getattr(self.instance, "frontend_url", ""))
        landing = attrs.get("landing_url", getattr(self.instance, "landing_url", ""))
        if same_link(frontend, landing):
            raise serializers.ValidationError("进入游戏和落地页不能是同一个链接")
        return _store_texts(self, attrs, GAME_FIELDS, GAME_LIMITS)

    def validate_code(self, value):
        if not value:
            return None
        queryset = OtomeGame.objects.filter(code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("故事编码已存在")
        return value

    def validate_play_package(self, value):
        package = clean_package(value)
        if package is None:
            raise serializers.ValidationError("Google 包名格式不正确")
        return package

    def validate_ios_app_id(self, value):
        ios_id = clean_ios(value)
        if ios_id is None:
            raise serializers.ValidationError("App Store ID 应是数字")
        return ios_id

    def validate_cover(self, value):
        _ensure_visual(value, "竖屏封面")
        return value

    def validate_cover_land(self, value):
        _ensure_visual(value, "横屏封面")
        return value


class GameListSerializer(serializers.ModelSerializer):
    """故事列表只返回表格上的列。"""

    play_url = serializers.SerializerMethodField()
    landing_page_url = serializers.SerializerMethodField()
    node_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = OtomeGame
        fields = [
            "id", "title", "subtitle", "lang", "status",
            "play_url", "landing_page_url", "node_count", "sort_order",
        ]

    def get_play_url(self, obj):
        return resolve_frontend_url(obj)

    def get_landing_page_url(self, obj):
        return resolve_landing_url(obj, self.context.get("request"))


class GameBriefSerializer(serializers.ModelSerializer):
    """下拉框只需要编号和标题。"""

    class Meta:
        model = OtomeGame
        fields = ["id", "title"]


class CharacterSerializer(LangSerializerMixin, serializers.ModelSerializer):
    portrait_url = serializers.SerializerMethodField()
    portrait_land_url = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = OtomeCharacter
        fields = [
            "id", "game", "name", "title", "portrait", "portrait_url",
            "portrait_land", "portrait_land_url", "images",
            "name_color", "intro", "texts", "lang", "sort_order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "portrait_url", "portrait_land_url", "images", "created_at", "updated_at"]
        extra_kwargs = {
            "game": {"help_text": "所属故事 ID"},
            "name": {"help_text": "角色名"},
            "title": {"required": False, "allow_blank": True},
            "portrait": {"required": False, "allow_null": True, "help_text": "竖屏立绘，图片 1080×1920，或循环播放的视频"},
            "portrait_land": {"required": False, "allow_null": True, "help_text": "横屏立绘，图片 1920×1080，或循环播放的视频"},
            "name_color": {"required": False, "allow_blank": True},
            "intro": {"required": False, "allow_blank": True},
            "lang": {"required": False, "allow_blank": True},
            "texts": {"required": False},
        }

    def validate(self, attrs):
        return _store_texts(self, attrs, CHARACTER_FIELDS, CHARACTER_LIMITS)

    def get_portrait_url(self, obj):
        return resolve_asset_url(obj.portrait, self.context.get("request"))

    def get_portrait_land_url(self, obj):
        return resolve_asset_url(obj.portrait_land, self.context.get("request"))

    def validate_portrait(self, value):
        _ensure_visual(value, "竖屏立绘")
        return value

    def validate_portrait_land(self, value):
        _ensure_visual(value, "横屏立绘")
        return value

    def get_images(self, obj):
        rows = []
        for item in obj.images.all():
            rows.append({
                "id": item.id,
                "label": item.label,
                "texts": item.texts or {},
                "image": item.image_id,
                "image_land": item.image_land_id,
                "image_url": resolve_asset_url(item.image, self.context.get("request")),
                "image_land_url": resolve_asset_url(item.image_land, self.context.get("request")),
                "screen_size": item.screen_size,
                "sort_order": item.sort_order,
            })
        return rows

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._save_images(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._save_images(instance)
        return instance

    def _save_images(self, character):
        rows = self.initial_data.get("images")
        if not isinstance(rows, list):
            return
        kept = []
        game_id = character.game_id
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            image_id = row.get("image") or None
            if not image_id:
                continue
            asset = OtomeAsset.objects.filter(id=image_id, is_deleted=False).first()
            if asset is None or asset.asset_type not in (OtomeAsset.TYPE_IMAGE, OtomeAsset.TYPE_VIDEO):
                raise serializers.ValidationError("立绘必须是图片或视频")
            if asset.game_id not in (None, game_id):
                raise serializers.ValidationError("立绘属于别的游戏")
            land_id = row.get("image_land") or None
            land = None
            if land_id:
                land = OtomeAsset.objects.filter(id=land_id, is_deleted=False).first()
                if land is None or land.asset_type not in (OtomeAsset.TYPE_IMAGE, OtomeAsset.TYPE_VIDEO):
                    raise serializers.ValidationError("横屏立绘必须是图片或视频")
                if land.game_id not in (None, game_id):
                    raise serializers.ValidationError("横屏立绘属于别的游戏")
            item = None
            if row.get("id"):
                item = OtomeCharacterImage.objects.filter(id=row.get("id"), character=character).first()
            if item is None:
                item = OtomeCharacterImage(character=character)
            item.label = str(row.get("label") or "")[:50]
            try:
                item.texts = clean_texts(row.get("texts"), IMAGE_FIELDS, IMAGE_LIMITS, character.lang)
            except ValueError:
                raise serializers.ValidationError("多语言格式不正确")
            item.image = asset
            item.image_land = land
            item.screen_size = _screen_size(row.get("screen_size"))
            item.sort_order = index
            item.save()
            kept.append(item.id)
        character.images.exclude(id__in=kept).delete()
        first = character.images.order_by("sort_order", "id").first()
        character.portrait = first.image if first else None
        character.portrait_land = first.image_land if first else None
        character.save(update_fields=["portrait", "portrait_land", "updated_at"])


class AssetBriefSerializer(serializers.ModelSerializer):
    """下拉框带上可访问地址，供试听和预览。节点详情的 *_info 也用这一份。"""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = OtomeAsset
        fields = ["id", "name", "asset_type", "file_url", "duration", "file_size"]

    def get_file_url(self, obj):
        return resolve_asset_url(obj, self.context.get("request"))


class AssetListSerializer(serializers.ModelSerializer):
    """素材表格显示语言、名称，并带上可访问地址，供预览使用。"""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = OtomeAsset
        fields = ["id", "name", "lang", "asset_type", "file_url", "duration", "file_size"]

    def get_file_url(self, obj):
        return resolve_asset_url(obj, self.context.get("request"))


class ChoiceSerializer(serializers.ModelSerializer):
    interact_info = AssetBriefSerializer(source="interact", read_only=True, allow_null=True)

    class Meta:
        model = OtomeChoice
        fields = [
            "id", "node", "text", "texts", "next_node", "interact", "interact_info",
            "sort_order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "interact_info", "created_at", "updated_at"]
        extra_kwargs = {
            "node": {"help_text": "所在剧情 ID"},
            "text": {"help_text": "选项文字"},
            "texts": {"required": False},
            "next_node": {"help_text": "跳转到的剧情 ID"},
            "interact": {"required": False, "allow_null": True, "help_text": "点这个选项时播放一次的音频"},
        }

    def validate(self, attrs):
        node = attrs.get("node") or getattr(self.instance, "node", None)
        next_node = attrs.get("next_node") or getattr(self.instance, "next_node", None)
        if node and next_node and node.game_id != next_node.game_id:
            raise serializers.ValidationError("选项只能跳转到同一部故事里的剧情")
        if next_node and next_node.is_deleted:
            raise serializers.ValidationError("不能跳转到已删除的剧情")
        interact = attrs.get("interact") if "interact" in attrs else getattr(self.instance, "interact", None)
        _ensure_type(interact, OtomeAsset.TYPE_AUDIO, "选项交互音频")
        node = attrs.get("node") or getattr(self.instance, "node", None)
        source = node.lang if node is not None else "zh-Hans"
        return _store_texts(self, attrs, CHOICE_FIELDS, CHOICE_LIMITS, source)


class ChoiceReadSerializer(serializers.ModelSerializer):
    interact_info = AssetBriefSerializer(source="interact", read_only=True, allow_null=True)

    class Meta:
        model = OtomeChoice
        fields = ["id", "text", "texts", "next_node", "interact", "interact_info", "sort_order"]


class ChoiceBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtomeChoice
        fields = ["id", "text", "next_node", "sort_order"]


class NodeListSerializer(serializers.ModelSerializer):
    """剧情列表不带立绘和选项，避免一页把整部故事的关联都查出来。"""

    class Meta:
        model = OtomeNode
        fields = [
            "id", "game", "node_key", "sort_order", "character", "speaker_name", "content",
            "is_start", "is_key", "is_ending", "lang", "next_node",
        ]


class NodeGraphSerializer(NodeListSerializer):
    """流程图只多带选项的跳转，不带立绘。"""

    choices = ChoiceBriefSerializer(many=True, read_only=True)

    class Meta(NodeListSerializer.Meta):
        fields = NodeListSerializer.Meta.fields + ["choices"]


class GalleryListSerializer(serializers.ModelSerializer):
    """解锁表格只显示语言、标题、类型。编辑时再取详情。"""

    class Meta:
        model = OtomeGalleryItem
        fields = ["id", "lang", "title", "kind"]


class NodeSerializer(LangSerializerMixin, serializers.ModelSerializer):
    choices = ChoiceReadSerializer(many=True, read_only=True)
    figures = serializers.SerializerMethodField()
    background_info = AssetBriefSerializer(source="background", read_only=True, allow_null=True)
    background_land_info = AssetBriefSerializer(source="background_land", read_only=True, allow_null=True)
    portrait_info = AssetBriefSerializer(source="portrait", read_only=True, allow_null=True)
    portrait_land_info = AssetBriefSerializer(source="portrait_land", read_only=True, allow_null=True)
    bgm_info = AssetBriefSerializer(source="bgm", read_only=True, allow_null=True)
    voice_info = AssetBriefSerializer(source="voice", read_only=True, allow_null=True)
    interact_info = AssetBriefSerializer(source="interact", read_only=True, allow_null=True)
    insert_media_info = AssetBriefSerializer(source="insert_media", read_only=True, allow_null=True)

    class Meta:
        model = OtomeNode
        fields = [
            "id", "game", "node_key", "sort_order", "character", "speaker_name", "content",
            "background", "background_info", "background_land", "background_land_info",
            "portrait", "portrait_info", "portrait_land", "portrait_land_info",
            "bgm", "bgm_info", "voice", "voice_info", "interact", "interact_info",
            "insert_media", "insert_media_info", "insert_title", "next_node",
            "is_start", "is_key", "is_ending", "ending_title", "texts", "lang", "cast_mode", "figures", "choices",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "figures", "choices",
            "background_info", "background_land_info", "portrait_info", "portrait_land_info",
            "bgm_info", "voice_info", "interact_info", "insert_media_info",
            "created_at", "updated_at",
        ]
        extra_kwargs = {
            "game": {"help_text": "所属故事 ID"},
            "node_key": {"help_text": "同一故事内唯一的剧情编号"},
            "content": {"help_text": "玩家看到的对白或旁白"},
            "speaker_name": {"required": False, "allow_blank": True},
            "character": {"required": False, "allow_null": True},
            "background": {"required": False, "allow_null": True, "help_text": "竖屏背景，图片 1080×1920，或循环播放的视频"},
            "background_land": {"required": False, "allow_null": True, "help_text": "横屏背景，图片 1920×1080，或循环播放的视频"},
            "portrait": {"required": False, "allow_null": True, "help_text": "竖屏立绘，图片 1080×1920，或循环播放的视频"},
            "portrait_land": {"required": False, "allow_null": True, "help_text": "横屏立绘，图片 1920×1080，或循环播放的视频"},
            "bgm": {"required": False, "allow_null": True},
            "voice": {"required": False, "allow_null": True},
            "interact": {"required": False, "allow_null": True, "help_text": "玩家点击这段对白时播放一次"},
            "insert_media": {"required": False, "allow_null": True, "help_text": "对白结束后全屏播放的视频或图片，玩家可点击跳过"},
            "insert_title": {"required": False, "allow_blank": True, "help_text": "故事解锁里显示的名字，留空则用素材名"},
            "next_node": {"required": False, "allow_null": True},
            "ending_title": {"required": False, "allow_blank": True},
            "texts": {"required": False},
            "is_key": {"help_text": "关键节点。进入前客户端会下载这一段资源"},
            "cast_mode": {"help_text": "single 单角色，multi 多角色"},
            "lang": {"required": False, "allow_blank": True},
        }

    def get_figures(self, obj):
        rows = []
        for item in obj.figures.all():
            rows.append({
                "id": item.id,
                "character": item.character_id,
                "image": item.image_id,
                "position": item.position,
                "sort_order": item.sort_order,
            })
        return rows

    def validate_node_key(self, value):
        game_id = self.initial_data.get("game") or getattr(self.instance, "game_id", None)
        if not game_id:
            return value
        queryset = OtomeNode.objects.filter(game_id=game_id, node_key=value, is_deleted=False)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("同一部故事里的剧情编号不能重复")
        return value

    def validate(self, attrs):
        game = attrs.get("game") or getattr(self.instance, "game", None)
        next_node = attrs.get("next_node") if "next_node" in attrs else getattr(self.instance, "next_node", None)
        character = attrs.get("character") if "character" in attrs else getattr(self.instance, "character", None)
        if game and next_node and next_node.game_id != game.id:
            raise serializers.ValidationError("下一句必须属于同一部故事")
        if game and character and character.game_id != game.id:
            raise serializers.ValidationError("说话的角色必须属于同一部故事")
        if "background" in attrs:
            _ensure_visual(attrs.get("background"), "竖屏背景")
        if "background_land" in attrs:
            _ensure_visual(attrs.get("background_land"), "横屏背景")
        if "portrait" in attrs:
            _ensure_visual(attrs.get("portrait"), "竖屏立绘")
        if "portrait_land" in attrs:
            _ensure_visual(attrs.get("portrait_land"), "横屏立绘")
        if "bgm" in attrs:
            _ensure_type(attrs.get("bgm"), OtomeAsset.TYPE_AUDIO, "背景音乐")
        if "voice" in attrs:
            _ensure_type(attrs.get("voice"), OtomeAsset.TYPE_AUDIO, "语音")
        if "interact" in attrs:
            _ensure_type(attrs.get("interact"), OtomeAsset.TYPE_AUDIO, "交互音频")
        if "insert_media" in attrs:
            asset = attrs.get("insert_media")
            _ensure_visual(asset, "插入内容")
            if asset is not None and game and asset.game_id not in (None, game.id):
                raise serializers.ValidationError("插入内容属于别的游戏")
        return _store_texts(self, attrs, NODE_FIELDS, NODE_LIMITS)

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._save_figures(instance)
        self._single_start(instance)
        sync_insert_gallery(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._save_figures(instance)
        self._single_start(instance)
        sync_insert_gallery(instance)
        return instance

    def _save_figures(self, node):
        rows = self.initial_data.get("figures")
        if not isinstance(rows, list):
            return
        if node.cast_mode not in (OtomeNode.CAST_SINGLE, OtomeNode.CAST_MULTI):
            node.cast_mode = OtomeNode.CAST_SINGLE
            node.save(update_fields=["cast_mode", "updated_at"])
        if node.cast_mode == OtomeNode.CAST_SINGLE:
            rows = rows[:1]
        allowed = {code for code, _label in OtomeNodeFigure.POSITIONS}
        ready = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            character = None
            character_id = row.get("character") or None
            if character_id:
                character = OtomeCharacter.objects.filter(id=character_id, game_id=node.game_id, is_deleted=False).first()
                if character is None:
                    raise serializers.ValidationError("画面上的角色必须属于这部故事")
            image = None
            image_id = row.get("image") or None
            if image_id:
                image = OtomeCharacterImage.objects.filter(id=image_id).select_related("character").first()
                if image is None or image.character.game_id != node.game_id or image.character.is_deleted:
                    raise serializers.ValidationError("立绘不属于这部故事")
                if character is not None and image.character_id != character.id:
                    raise serializers.ValidationError("立绘必须属于画面上的这个角色")
                if character is None:
                    character = image.character
            if character is None and image is None:
                continue
            position = row.get("position") or "c"
            if position not in allowed:
                position = "c"
            ready.append((character, image, position))
        node.figures.all().delete()
        for index, (character, image, position) in enumerate(ready):
            OtomeNodeFigure.objects.create(
                node=node,
                character=character,
                image=image,
                position=position,
                sort_order=index,
            )
        first = node.figures.select_related("image").order_by("sort_order", "id").first()
        node.portrait = first.image.image if first and first.image_id else None
        node.portrait_land = first.image.image_land if first and first.image_id else None
        node.save(update_fields=["portrait", "portrait_land", "updated_at"])

    def _single_start(self, instance):
        if instance.is_start:
            OtomeNode.objects.filter(game_id=instance.game_id, is_start=True).exclude(pk=instance.pk).update(is_start=False)


class GalleryItemSerializer(LangSerializerMixin, serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = OtomeGalleryItem
        fields = [
            "id", "game", "kind", "asset", "title", "texts", "unlock_node",
            "unlocked_by_default", "lang", "sort_order", "media_url",
        ]
        read_only_fields = ["id", "media_url"]
        extra_kwargs = {
            "asset": {"required": True, "allow_null": False},
            "unlock_node": {"required": False, "allow_null": True},
            "title": {"help_text": "在故事解锁里显示的名字"},
            "kind": {"help_text": "video 视频，portrait 立绘"},
            "lang": {"required": False, "allow_blank": True},
            "texts": {"required": False},
        }

    def get_media_url(self, obj):
        return resolve_asset_url(obj.asset, self.context.get("request"))

    def validate(self, attrs):
        game = attrs.get("game") or getattr(self.instance, "game", None)
        asset = attrs.get("asset") if "asset" in attrs else getattr(self.instance, "asset", None)
        kind = attrs.get("kind") or getattr(self.instance, "kind", "")
        unlock_node = attrs.get("unlock_node") if "unlock_node" in attrs else getattr(self.instance, "unlock_node", None)
        if asset is None or asset.is_deleted:
            raise serializers.ValidationError("请选择素材")
        if kind == OtomeGalleryItem.KIND_VIDEO and asset.asset_type != OtomeAsset.TYPE_VIDEO:
            raise serializers.ValidationError("视频解锁要选视频素材")
        if kind == OtomeGalleryItem.KIND_PORTRAIT and asset.asset_type != OtomeAsset.TYPE_IMAGE:
            raise serializers.ValidationError("立绘解锁要选图片素材")
        if game and asset.game_id not in (None, game.id):
            raise serializers.ValidationError("素材属于别的游戏")
        if game and unlock_node and unlock_node.game_id != game.id:
            raise serializers.ValidationError("解锁剧情必须属于同一部游戏")
        if game and asset.game_id is None:
            asset.game = game
            asset.save(update_fields=["game", "updated_at"])
        return _store_texts(self, attrs, GALLERY_FIELDS, GALLERY_LIMITS)
