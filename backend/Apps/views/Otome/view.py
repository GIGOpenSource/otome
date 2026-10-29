import logging
import os

from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from Apps.views.Otome.permissions import (
    IsOtomeAdmin,
    current_staff,
    ensure_game_access,
    scope_to_visible_games,
    sees_all_games,
    visible_games,
)
from Apps.views.Otome.content_i18n import ASSET_FIELDS, ASSET_LIMITS, clean_texts, field_text
from Apps.views.Otome.i18n import clean_lang, filter_lang
from Apps.views.Otome.script import build_script, resolve_asset_url
from Apps.views.Otome.serializers import (
    AssetBriefSerializer,
    AssetSerializer,
    CharacterSerializer,
    ChoiceSerializer,
    AssetListSerializer,
    GalleryItemSerializer,
    GalleryListSerializer,
    GameBriefSerializer,
    GameListSerializer,
    GameSerializer,
    NodeGraphSerializer,
    NodeListSerializer,
    NodeSerializer,
)
from django.db.models import Count, IntegerField, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce

from Apps.views.Otome.ads import retire_ads_for_game
from models.models import OtomeAsset, OtomeCharacter, OtomeChoice, OtomeGalleryItem, OtomeGame, OtomeNode
from tools.base_views import BaseViewSet
from tools.minio_storage import store_upload
from tools.utils import ApiResponse, CustomPagination

logger = logging.getLogger(__name__)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
VIDEO_EXT = {".mp4", ".webm", ".mov"}


def apply_upload_meta(asset, upload, data):
    """记下文件字节数。音频再记下前端传来的时长（秒）。"""
    try:
        asset.file_size = max(int(upload.size or 0), 0)
    except (TypeError, ValueError):
        asset.file_size = 0
    if getattr(asset, "asset_type", "") != OtomeAsset.TYPE_AUDIO:
        asset.duration = None
        return
    raw = data.get("duration")
    if raw in (None, ""):
        asset.duration = None
        return
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        asset.duration = None
        return
    if seconds < 0:
        seconds = 0
    asset.duration = round(seconds, 2)


def _soft_delete(instance):
    instance.is_deleted = True
    instance.save(update_fields=["is_deleted", "updated_at"])


@extend_schema(tags=[_("乙游素材")])
@extend_schema_view(
    list=extend_schema(summary=_("素材列表"), parameters=[
        OpenApiParameter(name="asset_type", type=str, description="image 或 audio"),
        OpenApiParameter(name="name", type=str, description="名称模糊搜索"),
    ]),
    retrieve=extend_schema(summary=_("素材详情")),
    create=extend_schema(summary=_("用外链创建素材")),
    update=extend_schema(summary=_("更新素材")),
    partial_update=extend_schema(summary=_("部分更新素材")),
    destroy=extend_schema(summary=_("删除素材")),
)
class AssetViewSet(BaseViewSet):
    serializer_class = AssetSerializer
    pagination_class = CustomPagination
    permission_classes = [IsOtomeAdmin]

    def get_serializer_class(self):
        if self.action != "list":
            return AssetSerializer
        if self.request.query_params.get("brief") == "1":
            return AssetBriefSerializer
        return AssetListSerializer

    def get_queryset(self):
        queryset = OtomeAsset.objects.filter(is_deleted=False).order_by("-id")
        asset_type = self.request.query_params.get("asset_type")
        name = self.request.query_params.get("name")
        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)
        if name:
            queryset = queryset.filter(name__icontains=name)
        queryset = filter_lang(queryset, self.request.query_params.get("lang"))
        game_id = self.request.query_params.get("game")
        if game_id:
            if not sees_all_games(self.request) and not visible_games(self.request).filter(id=game_id).exists():
                return queryset.none()
            queryset = queryset.filter(game_id=game_id)
        elif not sees_all_games(self.request):
            queryset = queryset.filter(Q(game__isnull=True) | Q(game__in=visible_games(self.request)))
        if self.action == "list":
            if self.request.query_params.get("brief") == "1":
                queryset = queryset.only(
                    "id", "name", "asset_type", "url", "file", "is_deleted", "duration", "file_size",
                )
            else:
                queryset = queryset.only(
                    "id", "name", "lang", "asset_type", "url", "file", "is_deleted", "duration", "file_size",
                )
        return queryset

    def perform_create(self, serializer):
        ensure_game_access(self.request, serializer.validated_data.get("game"))
        serializer.save()

    def perform_update(self, serializer):
        game = serializer.validated_data.get("game", getattr(serializer.instance, "game", None))
        ensure_game_access(self.request, game)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            _soft_delete(instance)
            logger.info("删除乙游素材 id=%s", instance.id)
            return ApiResponse(message="删除成功")
        except Exception:
            logger.error("删除素材失败", exc_info=True)
            return ApiResponse(message="删除失败", code=500)


@extend_schema(tags=[_("乙游素材")], summary=_("上传或替换图片、音频"))
class AssetUploadView(APIView):
    permission_classes = [IsOtomeAdmin]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return ApiResponse(message="请选择文件", code=400)
        ext = os.path.splitext(upload.name)[1].lower()[:8]
        asset_type = request.data.get("asset_type") or ""
        if not asset_type:
            if ext in IMAGE_EXT:
                asset_type = OtomeAsset.TYPE_IMAGE
            elif ext in AUDIO_EXT:
                asset_type = OtomeAsset.TYPE_AUDIO
            elif ext in VIDEO_EXT:
                asset_type = OtomeAsset.TYPE_VIDEO
        if asset_type == OtomeAsset.TYPE_IMAGE and ext not in IMAGE_EXT:
            return ApiResponse(message="图片只支持 jpg、png、webp、gif、svg", code=400)
        if asset_type == OtomeAsset.TYPE_AUDIO and ext not in AUDIO_EXT:
            return ApiResponse(message="音频只支持 mp3、wav、m4a、aac、ogg", code=400)
        if asset_type == OtomeAsset.TYPE_VIDEO and ext not in VIDEO_EXT:
            return ApiResponse(message="视频只支持 mp4、webm、mov", code=400)
        if asset_type not in (OtomeAsset.TYPE_IMAGE, OtomeAsset.TYPE_AUDIO, OtomeAsset.TYPE_VIDEO):
            return ApiResponse(message="类型只能是 image、audio 或 video", code=400)
        limit = 80 * 1024 * 1024 if asset_type == OtomeAsset.TYPE_VIDEO else 20 * 1024 * 1024
        if upload.size > limit:
            return ApiResponse(message="视频不能超过 80MB" if asset_type == OtomeAsset.TYPE_VIDEO else "文件不能超过 20MB", code=400)
        try:
            asset_id = request.data.get("asset_id")
            if asset_id:
                asset = OtomeAsset.objects.get(id=asset_id, is_deleted=False)
                asset.asset_type = asset_type
                if request.data.get("name"):
                    asset.name = request.data.get("name")
            else:
                asset = OtomeAsset(
                    name=request.data.get("name") or upload.name,
                    asset_type=asset_type,
                    remark=request.data.get("remark") or "",
                )
            lang = clean_lang(request.data.get("lang"))
            if lang is None:
                return ApiResponse(message="请选择语言", code=400)
            asset.lang = lang
            if "texts" in request.data:
                try:
                    asset.texts = clean_texts(request.data.get("texts"), ASSET_FIELDS, ASSET_LIMITS, lang)
                except ValueError:
                    return ApiResponse(message="多语言格式不正确", code=400)
            if asset.file:
                asset.file.delete(save=False)
            asset.file = None
            if asset_id and asset.game_id:
                try:
                    ensure_game_access(request, asset.game)
                except ValidationError:
                    return ApiResponse(message="不能操作这部游戏", code=403)
            game_id = request.data.get("game")
            if game_id:
                try:
                    game = OtomeGame.objects.filter(id=int(game_id), is_deleted=False).first()
                except (TypeError, ValueError):
                    return ApiResponse(message="故事不存在", code=404)
                if game is None:
                    return ApiResponse(message="故事不存在", code=404)
                try:
                    ensure_game_access(request, game)
                except ValidationError:
                    return ApiResponse(message="不能操作这部游戏", code=403)
                asset.game = game
            try:
                asset.url = store_upload(upload, ext)
            except Exception as exc:
                logger.error("上传到 MinIO 失败", exc_info=True)
                return ApiResponse(message=f"上传到文件存储失败：{exc}", code=500)
            apply_upload_meta(asset, upload, request.data)
            asset.save()
            logger.info("上传乙游素材 id=%s type=%s", asset.id, asset.asset_type)
            data = AssetSerializer(asset, context={"request": request}).data
            return ApiResponse(data=data, message="上传成功", code=201)
        except OtomeAsset.DoesNotExist:
            return ApiResponse(message="要替换的素材不存在", code=404)
        except Exception:
            logger.error("上传素材失败", exc_info=True)
            return ApiResponse(message="上传失败", code=500)


@extend_schema(tags=[_("乙游故事")])
@extend_schema_view(
    list=extend_schema(summary=_("故事列表")),
    retrieve=extend_schema(summary=_("故事详情")),
    create=extend_schema(summary=_("创建故事")),
    update=extend_schema(summary=_("更新故事")),
    partial_update=extend_schema(summary=_("部分更新故事")),
    destroy=extend_schema(summary=_("删除故事")),
)
class GameViewSet(BaseViewSet):
    serializer_class = GameSerializer
    pagination_class = CustomPagination
    permission_classes = [IsOtomeAdmin]

    def get_serializer_class(self):
        if self.action != "list":
            return GameSerializer
        if self.request.query_params.get("brief") == "1":
            return GameBriefSerializer
        return GameListSerializer

    def get_queryset(self):
        queryset = visible_games(self.request).order_by("sort_order", "-id")
        brief = self.request.query_params.get("brief") == "1"
        if self.action == "list" and not brief:
            alive_nodes = (
                OtomeNode.objects.filter(game_id=OuterRef("pk"), is_deleted=False)
                .values("game_id")
                .annotate(total=Count("id"))
                .values("total")
            )
            queryset = queryset.annotate(
                node_count=Coalesce(Subquery(alive_nodes, output_field=IntegerField()), 0)
            ).defer("summary", "texts", "play_package", "ios_app_id")
        elif self.action != "list":
            queryset = queryset.select_related("cover", "cover_land")
        return filter_lang(queryset, self.request.query_params.get("lang"))

    def perform_create(self, serializer):
        serializer.save(created_by=current_staff(self.request))

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            _soft_delete(instance)
            retire_ads_for_game(instance)
            logger.info("删除乙游故事 id=%s", instance.id)
            return ApiResponse(message="删除成功")
        except Exception:
            logger.error("删除故事失败", exc_info=True)
            return ApiResponse(message="删除失败", code=500)


@extend_schema(tags=[_("乙游角色")])
@extend_schema_view(
    list=extend_schema(summary=_("角色列表"), parameters=[
        OpenApiParameter(name="game", type=int, description="故事 ID"),
    ]),
    retrieve=extend_schema(summary=_("角色详情")),
    create=extend_schema(summary=_("创建角色")),
    update=extend_schema(summary=_("更新角色")),
    partial_update=extend_schema(summary=_("部分更新角色")),
    destroy=extend_schema(summary=_("删除角色")),
)
class CharacterViewSet(BaseViewSet):
    serializer_class = CharacterSerializer
    pagination_class = CustomPagination
    permission_classes = [IsOtomeAdmin]

    def get_queryset(self):
        queryset = (
            OtomeCharacter.objects.filter(is_deleted=False)
            .select_related("portrait", "portrait_land")
            .prefetch_related("images", "images__image", "images__image_land")
            .order_by("sort_order", "id")
        )
        game_id = self.request.query_params.get("game")
        if game_id:
            queryset = queryset.filter(game_id=game_id)
        queryset = filter_lang(queryset, self.request.query_params.get("lang"))
        return scope_to_visible_games(queryset, self.request)

    def perform_create(self, serializer):
        ensure_game_access(self.request, serializer.validated_data.get("game"))
        serializer.save()

    def perform_update(self, serializer):
        game = serializer.validated_data.get("game", serializer.instance.game)
        ensure_game_access(self.request, game)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            _soft_delete(instance)
            return ApiResponse(message="删除成功")
        except Exception:
            logger.error("删除角色失败", exc_info=True)
            return ApiResponse(message="删除失败", code=500)


@extend_schema(tags=[_("乙游剧情")])
@extend_schema_view(
    list=extend_schema(summary=_("剧情列表"), parameters=[
        OpenApiParameter(name="game", type=int, description="故事 ID"),
    ]),
    retrieve=extend_schema(summary=_("剧情详情")),
    create=extend_schema(summary=_("创建剧情")),
    update=extend_schema(summary=_("更新剧情")),
    partial_update=extend_schema(summary=_("部分更新剧情")),
    destroy=extend_schema(summary=_("删除剧情")),
)
class NodeViewSet(BaseViewSet):
    serializer_class = NodeSerializer
    pagination_class = CustomPagination
    permission_classes = [IsOtomeAdmin]

    def get_serializer_class(self):
        if self.action != "list":
            return NodeSerializer
        if self.request.query_params.get("graph") == "1":
            return NodeGraphSerializer
        return NodeListSerializer

    def get_queryset(self):
        queryset = OtomeNode.objects.filter(is_deleted=False).order_by("sort_order", "id")
        if self.action == "list":
            if self.request.query_params.get("graph") == "1":
                queryset = queryset.prefetch_related(
                    Prefetch(
                        "choices",
                        queryset=OtomeChoice.objects.only(
                            "id", "text", "next_node", "sort_order", "node",
                        ).order_by("sort_order", "id"),
                    )
                ).defer(
                    "texts", "ending_title", "insert_title",
                    "background", "background_land", "portrait", "portrait_land",
                    "bgm", "voice", "interact", "insert_media",
                )
            else:
                queryset = queryset.only(
                    "id", "game", "node_key", "sort_order", "character", "speaker_name", "content",
                    "is_start", "is_key", "is_ending", "lang", "next_node",
                )
        else:
            queryset = queryset.select_related(
                "background", "background_land", "portrait", "portrait_land",
                "bgm", "voice", "interact", "insert_media",
            ).prefetch_related(
                "figures",
                Prefetch(
                    "choices",
                    queryset=OtomeChoice.objects.select_related("interact").order_by("sort_order", "id"),
                ),
            )
        game_id = self.request.query_params.get("game")
        if game_id:
            queryset = queryset.filter(game_id=game_id)
        queryset = filter_lang(queryset, self.request.query_params.get("lang"))
        return scope_to_visible_games(queryset, self.request)

    def perform_create(self, serializer):
        ensure_game_access(self.request, serializer.validated_data.get("game"))
        serializer.save()

    def perform_update(self, serializer):
        game = serializer.validated_data.get("game", serializer.instance.game)
        ensure_game_access(self.request, game)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.is_deleted = True
            instance.is_start = False
            instance.save(update_fields=["is_deleted", "is_start", "updated_at"])
            instance.choices.all().delete()
            OtomeChoice.objects.filter(next_node=instance).delete()
            OtomeNode.objects.filter(next_node=instance).update(next_node=None)
            logger.info("删除乙游剧情 id=%s", instance.id)
            return ApiResponse(message="删除成功")
        except Exception:
            logger.error("删除剧情失败", exc_info=True)
            return ApiResponse(message="删除失败", code=500)


@extend_schema(tags=[_("乙游选项")])
@extend_schema_view(
    list=extend_schema(summary=_("选项列表"), parameters=[
        OpenApiParameter(name="node", type=int, description="剧情 ID"),
        OpenApiParameter(name="game", type=int, description="故事 ID"),
    ]),
    retrieve=extend_schema(summary=_("选项详情")),
    create=extend_schema(summary=_("创建选项")),
    update=extend_schema(summary=_("更新选项")),
    partial_update=extend_schema(summary=_("部分更新选项")),
    destroy=extend_schema(summary=_("删除选项")),
)
class ChoiceViewSet(BaseViewSet):
    serializer_class = ChoiceSerializer
    pagination_class = CustomPagination
    permission_classes = [IsOtomeAdmin]
    queryset = OtomeChoice.objects.all().order_by("sort_order", "id")

    def get_queryset(self):
        queryset = OtomeChoice.objects.select_related("interact").order_by("sort_order", "id")
        node_id = self.request.query_params.get("node")
        game_id = self.request.query_params.get("game")
        if node_id:
            queryset = queryset.filter(node_id=node_id)
        elif game_id:
            queryset = queryset.filter(node__game_id=game_id)
        return scope_to_visible_games(queryset, self.request, "node__game")

    def perform_create(self, serializer):
        node = serializer.validated_data.get("node")
        ensure_game_access(self.request, getattr(node, "game", None))
        serializer.save()

    def perform_update(self, serializer):
        node = serializer.validated_data.get("node", serializer.instance.node)
        ensure_game_access(self.request, getattr(node, "game", None))
        serializer.save()


@extend_schema(tags=[_("故事解锁")])
@extend_schema_view(
    list=extend_schema(summary=_("解锁内容列表"), parameters=[
        OpenApiParameter(name="game", type=int, description="游戏 ID"),
    ]),
    retrieve=extend_schema(summary=_("解锁内容详情")),
    create=extend_schema(summary=_("新增解锁内容")),
    update=extend_schema(summary=_("更新解锁内容")),
    partial_update=extend_schema(summary=_("部分更新解锁内容")),
    destroy=extend_schema(summary=_("删除解锁内容")),
)
class GalleryItemViewSet(BaseViewSet):
    serializer_class = GalleryItemSerializer
    pagination_class = CustomPagination
    permission_classes = [IsOtomeAdmin]

    def get_serializer_class(self):
        if self.action == "list":
            return GalleryListSerializer
        return GalleryItemSerializer

    def get_queryset(self):
        queryset = OtomeGalleryItem.objects.filter(is_deleted=False).order_by("sort_order", "id")
        game_id = self.request.query_params.get("game")
        if game_id:
            queryset = queryset.filter(game_id=game_id)
        queryset = filter_lang(queryset, self.request.query_params.get("lang"))
        queryset = scope_to_visible_games(queryset, self.request)
        if self.action == "list":
            queryset = queryset.only("id", "lang", "title", "kind", "sort_order")
        return queryset

    def perform_create(self, serializer):
        ensure_game_access(self.request, serializer.validated_data.get("game"))
        serializer.save()

    def perform_update(self, serializer):
        game = serializer.validated_data.get("game", serializer.instance.game)
        ensure_game_access(self.request, game)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            _soft_delete(instance)
            return ApiResponse(message="删除成功")
        except Exception:
            logger.error("删除解锁内容失败", exc_info=True)
            return ApiResponse(message="删除失败", code=500)


@extend_schema(tags=[_("乙游玩法")], summary=_("按故事编码或编号找到已发布的游戏"))
class GameResolveView(APIView):
    """进入游戏的地址是 /编码/。客户端用这一段找到对应的已发布故事。"""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        slug = (request.query_params.get("slug") or "").strip()[:80]
        if not slug:
            return ApiResponse(message="缺少故事标识", code=400)
        published = OtomeGame.objects.filter(
            is_deleted=False,
            status=OtomeGame.STATUS_PUBLISHED,
        )
        game = published.filter(code=slug).first()
        if game is None and slug.isdigit():
            game = published.filter(id=int(slug)).first()
        if game is None:
            return ApiResponse(message="故事不存在", code=404)
        return ApiResponse(data={"id": game.id, "code": game.code or ""})


_BOOT_STEPS = (
    ("script", "script/", 80),
    ("ads", "ads/", 10),
    ("config", "", 10),
)
_VIDEO_EXT = (".mp4", ".webm", ".mov", ".m4v", ".ogg")


def _published_game(slug):
    published = OtomeGame.objects.filter(
        is_deleted=False,
        status=OtomeGame.STATUS_PUBLISHED,
    ).select_related("cover", "cover_land")
    game = published.filter(code=slug).first()
    if game is None and slug.isdigit():
        game = published.filter(id=int(slug)).first()
    return game


def _media_kind(url):
    path = (url or "").split("?")[0].split("#")[0].lower()
    if path.endswith(_VIDEO_EXT):
        return "video"
    return "image"


def _opening_urls(game, request):
    portrait = (game.splash_url or "").strip() or resolve_asset_url(game.cover, request)
    landscape = (game.splash_land_url or "").strip() or resolve_asset_url(game.cover_land, request)
    return portrait, landscape


@extend_schema(tags=[_("乙游玩法")], summary=_("进入游戏前的开屏图和加载步骤"))
class GameBootView(APIView):
    """动态链接先拿开屏图。剧本等重接口列在 steps 里，由前端按权重累加进度。"""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        slug = (request.query_params.get("slug") or "").strip()[:80]
        if not slug:
            return ApiResponse(message="缺少故事标识", code=400)
        game = _published_game(slug)
        if game is None:
            return ApiResponse(message="故事不存在", code=404)
        portrait, landscape = _opening_urls(game, request)
        steps = []
        for key, suffix, weight in _BOOT_STEPS:
            if key == "config":
                path = "/api/otome/play/config/"
            else:
                path = f"/api/otome/play/games/{game.id}/{suffix}"
            steps.append({
                "key": key,
                "method": "GET",
                "path": path,
                "weight": weight,
                "required": True,
            })
        total = sum(item["weight"] for item in steps)
        return ApiResponse(data={
            "id": game.id,
            "code": game.code or "",
            "title": field_text(game, "title"),
            "splash_url": portrait,
            "splash_land_url": landscape,
            "splash_kind": _media_kind(portrait),
            "splash_land_kind": _media_kind(landscape),
            "steps": steps,
            "total_weight": total,
            "loaded_weight": 0,
            "progress": 0,
            "ready": False,
        })


@extend_schema(tags=[_("乙游玩法")], summary=_("按游戏 ID 获取可播放脚本和预下载清单"))
class GameScriptView(APIView):
    """单游戏客户端只拉这一份脚本。关键节点带 preload_urls。"""

    authentication_classes = []
    permission_classes = []

    def get(self, request, game_id):
        preview = request.query_params.get("preview") == "1"
        try:
            game = OtomeGame.objects.get(id=game_id, is_deleted=False)
        except OtomeGame.DoesNotExist:
            return ApiResponse(message="故事不存在", code=404)
        if game.status != OtomeGame.STATUS_PUBLISHED:
            if not preview or not IsOtomeAdmin().has_permission(request, self):
                return ApiResponse(message="故事未发布", code=404)
        try:
            data = build_script(game, request)
            logger.info("下发乙游脚本 game_id=%s nodes=%s", game.id, len(data["nodes"]))
            return ApiResponse(data=data)
        except Exception:
            logger.error("组装乙游脚本失败", exc_info=True)
            return ApiResponse(message="脚本生成失败", code=500)
