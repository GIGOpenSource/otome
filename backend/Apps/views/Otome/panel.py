import logging
import os
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render

from Apps.views.Otome.login_i18n import login_catalog, login_pack
from Apps.views.Otome.inserts import sync_insert_gallery
from Apps.views.Otome.script import resolve_asset_url
from Apps.views.Otome.specs import IMAGE_SPECS, check_upload_size, find_spec
from Apps.views.Otome.ads import channel_stats, new_channel_id, retire_ads_for_game, serialize_channel
from Apps.views.Otome.landing import clean_ios, clean_package
from Apps.views.Otome.links import clean_public_url, resolve_frontend_url, resolve_landing_url, same_link
from Apps.views.Otome.view import apply_upload_meta
from tools.minio_storage import store_upload
from models.models import (
    OtomeAdChannel,
    OtomeAsset,
    OtomeBuiltinAd,
    OtomeCharacter,
    OtomeChoice,
    OtomeDataRecord,
    OtomeGalleryItem,
    OtomeGame,
    OtomeNode,
    OtomePlayer,
    OtomePlayerGame,
    OtomeStaffGame,
    User,
)

logger = logging.getLogger(__name__)

COOKIE = "otome_panel"
LANG_COOKIE = "otome_lang"
SALT = "otome-panel"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
VIDEO_EXT = {".mp4", ".webm", ".mov"}
DATA_KIND_LABEL = dict(OtomeDataRecord.KIND_CHOICES)
STORY_TABS = ("info", "characters", "assets", "gallery", "plot")
NODE_TABS = ("line", "visual", "audio", "insert", "choice")
ACTION_TAB = {
    "meta": "info",
    "character": "characters",
    "delete_character": "characters",
    "upload": "assets",
    "url": "assets",
    "delete_asset": "assets",
    "gallery": "gallery",
    "delete_gallery": "gallery",
}


def _clean_tab(raw, allowed, default):
    value = (raw or "").strip()
    if value in allowed:
        return value
    return default


def _login_ok(request):
    token = request.COOKIES.get(COOKIE, "")
    if not token:
        return False
    try:
        data = signing.loads(token, salt=SALT, max_age=60 * 60 * 24 * 7)
    except Exception:
        return False
    return data.get("ok") is True


def panel_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not _login_ok(request):
            return redirect("/otome-admin/login/")
        return view(request, *args, **kwargs)
    return wrapper


def _set_login(response):
    response.set_cookie(
        COOKIE,
        signing.dumps({"ok": True}, salt=SALT),
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        samesite="Lax",
    )
    return response


def _fk(value):
    if value in (None, ""):
        return None
    return int(value)


def _checked(request, name):
    return request.POST.get(name) == "on"


def _asset_url(asset, request):
    return resolve_asset_url(asset, request)


def _apply_image_slot(asset, request, upload):
    if asset.asset_type != OtomeAsset.TYPE_IMAGE:
        asset.usage = ""
        asset.screen = ""
        return
    usage = (request.POST.get("usage") or "").strip()
    screen = (request.POST.get("screen") or "").strip()
    if upload is not None:
        check_upload_size(upload, usage, screen)
    elif find_spec(usage, screen) is None:
        raise ValueError("图片必须选择用途和横竖屏，并按对应像素制作")
    asset.usage = usage
    asset.screen = screen


def _asset_type_label(asset):
    if asset.asset_type == OtomeAsset.TYPE_VIDEO:
        return "视频"
    if asset.asset_type == OtomeAsset.TYPE_AUDIO:
        return "音频"
    spec = find_spec(asset.usage, asset.screen)
    if spec is None:
        return "图片 · 未标注尺寸"
    return f"图片 · {spec['title']}"


def _asset_spec_note(asset):
    spec = find_spec(asset.usage, asset.screen)
    if spec is None:
        return ""
    return f"{spec['width']} × {spec['height']}（{spec['ratio']}）"


def _bind_game(asset, game):
    if game is None:
        return
    if asset.game_id not in (None, game.id):
        raise ValueError("这件素材属于别的游戏")
    asset.game = game


def _referenced_asset_ids(game):
    ids = [game.cover_id, game.cover_land_id]
    for character in game.characters.filter(is_deleted=False):
        ids.extend([character.portrait_id, character.portrait_land_id])
    for node in game.nodes.filter(is_deleted=False):
        ids.extend([
            node.background_id,
            node.background_land_id,
            node.portrait_id,
            node.portrait_land_id,
            node.bgm_id,
            node.voice_id,
            node.interact_id,
        ])
        ids.extend(node.choices.values_list("interact_id", flat=True))
    return [item for item in ids if item]


def _assets_for_game(game, asset_type=None):
    query = Q(game=game) | Q(game__isnull=True) | Q(id__in=_referenced_asset_ids(game) or [0])
    queryset = OtomeAsset.objects.filter(is_deleted=False).filter(query)
    if asset_type:
        queryset = queryset.filter(asset_type=asset_type)
    return queryset.order_by("-id")


def _game_or_404(game_id):
    try:
        return OtomeGame.objects.get(id=game_id, is_deleted=False)
    except OtomeGame.DoesNotExist:
        raise Http404("故事不存在")


def _lang_code(request):
    raw = request.POST.get("lang") or request.GET.get("lang") or request.COOKIES.get(LANG_COOKIE) or "zh-Hans"
    pack = login_pack(raw)
    return pack["code"]


def _remember_lang(response, lang):
    response.set_cookie(LANG_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


def login_view(request):
    lang = _lang_code(request)
    ui = login_pack(lang)
    if _login_ok(request) and request.method == "GET" and not request.GET.get("lang"):
        return redirect("/otome-admin/")
    error = ""
    if request.method == "POST":
        key = (request.POST.get("key") or "").strip()
        expected = getattr(settings, "OTOME_ADMIN_KEY", "otome-demo")
        if key and key == expected:
            logger.info("乙游管理面板登录成功")
            response = redirect("/otome-admin/")
            _set_login(response)
            return _remember_lang(response, lang)
        logger.warning("乙游管理面板登录失败")
        error = ui["error"]
    hint = getattr(settings, "OTOME_ADMIN_KEY", "") if settings.DEBUG else ""
    response = render(request, "otome/login.html", {
        "error": error,
        "hint": hint,
        "ui": ui,
        "lang": lang,
        "dir": ui["dir"],
        "languages": login_catalog(),
    })
    return _remember_lang(response, lang)


def logout_view(request):
    response = redirect("/otome-admin/login/")
    response.delete_cookie(COOKIE)
    return response


@panel_required
def game_list(request):
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        if not title:
            games = OtomeGame.objects.filter(is_deleted=False).order_by("sort_order", "-id")
            return render(request, "otome/games.html", {"games": games, "error": "请填写故事标题"})
        game = OtomeGame.objects.create(
            title=title,
            subtitle=(request.POST.get("subtitle") or "").strip(),
            summary=(request.POST.get("summary") or "").strip(),
            status=OtomeGame.STATUS_DRAFT,
        )
        logger.info("管理面板创建故事 id=%s", game.id)
        return redirect(f"/otome-admin/games/{game.id}/")
    games = []
    for game in OtomeGame.objects.filter(is_deleted=False).order_by("sort_order", "-id"):
        games.append({
            "id": game.id,
            "title": game.title,
            "subtitle": game.subtitle,
            "status": game.status,
            "status_label": "已发布" if game.status == OtomeGame.STATUS_PUBLISHED else "草稿",
            "node_count": game.nodes.filter(is_deleted=False).count(),
            "play_url": resolve_frontend_url(game),
            "landing_page_url": resolve_landing_url(game, request),
        })
    return render(request, "otome/games.html", {"games": games, "error": request.GET.get("error", "")})


@panel_required
def game_edit(request, game_id):
    game = _game_or_404(game_id)
    error = request.GET.get("error", "")
    tab = _clean_tab(request.GET.get("tab"), STORY_TABS, "info")
    if request.method == "POST":
        action = request.POST.get("action")
        tab = ACTION_TAB.get(action, tab)
        try:
            if action == "meta":
                game.title = (request.POST.get("title") or "").strip()
                if not game.title:
                    error = "标题不能为空"
                else:
                    game.subtitle = (request.POST.get("subtitle") or "").strip()
                    game.summary = (request.POST.get("summary") or "").strip()
                    package = clean_package(request.POST.get("play_package"))
                    ios_id = clean_ios(request.POST.get("ios_app_id"))
                    if package is None:
                        error = "Google 包名格式不正确"
                    elif ios_id is None:
                        error = "App Store ID 应是数字"
                    else:
                        game.play_package = package
                        game.ios_app_id = ios_id
                        enter_url = clean_public_url(request.POST.get("frontend_url"))
                        page_url = clean_public_url(request.POST.get("landing_url"))
                        if enter_url is None:
                            error = "进入游戏的链接需要以 http:// 或 https:// 开头"
                        elif page_url is None:
                            error = "落地页链接需要以 http:// 或 https:// 开头"
                        elif same_link(enter_url, page_url):
                            error = "进入游戏和落地页不能是同一个链接"
                        else:
                            game.frontend_url = enter_url
                            game.landing_url = page_url
                            game.code = (request.POST.get("code") or "").strip() or None
                            game.cover_id = _fk(request.POST.get("cover"))
                            game.cover_land_id = _fk(request.POST.get("cover_land"))
                            game.status = OtomeGame.STATUS_PUBLISHED if _checked(request, "published") else OtomeGame.STATUS_DRAFT
                            if game.status == OtomeGame.STATUS_PUBLISHED and not game.nodes.filter(is_deleted=False).exists():
                                game.status = OtomeGame.STATUS_DRAFT
                                error = "先写至少一段剧情，再发布"
                            game.save()
                            logger.info("更新故事 id=%s status=%s", game.id, game.status)
            elif action == "delete":
                game.is_deleted = True
                game.save(update_fields=["is_deleted", "updated_at"])
                retire_ads_for_game(game)
                return redirect("/otome-admin/")
            elif action == "character":
                name = (request.POST.get("name") or "").strip()
                if not name:
                    error = "角色名不能为空"
                else:
                    character_id = _fk(request.POST.get("character_id"))
                    portrait_id = _fk(request.POST.get("portrait"))
                    portrait_land_id = _fk(request.POST.get("portrait_land"))
                    if character_id:
                        character = OtomeCharacter.objects.get(id=character_id, game=game, is_deleted=False)
                    else:
                        character = OtomeCharacter(game=game)
                    character.name = name
                    character.title = (request.POST.get("char_title") or "").strip()
                    character.name_color = (request.POST.get("name_color") or "#e7c27a").strip() or "#e7c27a"
                    character.intro = (request.POST.get("intro") or "").strip()
                    character.portrait_id = portrait_id
                    character.portrait_land_id = portrait_land_id
                    character.sort_order = int(request.POST.get("sort_order") or 0)
                    character.save()
            elif action == "delete_character":
                OtomeCharacter.objects.filter(id=_fk(request.POST.get("character_id")), game=game).update(is_deleted=True)
            elif action == "upload":
                error = _save_upload(request, game) or ""
            elif action == "url":
                _save_url_asset(request, game)
            elif action == "delete_asset":
                _delete_game_asset(request, game)
            elif action == "gallery":
                error = _save_gallery(request, game) or ""
            elif action == "delete_gallery":
                OtomeGalleryItem.objects.filter(
                    id=_fk(request.POST.get("item_id")), game=game,
                ).update(is_deleted=True)
            else:
                error = "无法识别的操作"
        except OtomeAsset.DoesNotExist:
            error = "素材不存在"
        except OtomeGalleryItem.DoesNotExist:
            error = "解锁内容不存在"
        except ValueError as exc:
            error = str(exc)
        except Exception:
            logger.error("保存故事失败", exc_info=True)
            error = error or "保存失败"
        if not error:
            return redirect(f"/otome-admin/games/{game.id}/?tab={tab}")
    images = _assets_for_game(game, OtomeAsset.TYPE_IMAGE)
    characters = []
    for item in game.characters.filter(is_deleted=False).order_by("sort_order", "id"):
        characters.append({
            "obj": item,
            "portrait_url": _asset_url(item.portrait, request),
            "portrait_land_url": _asset_url(item.portrait_land, request),
        })
    nodes = game.nodes.filter(is_deleted=False).order_by("sort_order", "id")
    return render(request, "otome/game.html", {
        "game": game,
        "images": images,
        "characters": characters,
        "nodes": nodes,
        "cover_url": _asset_url(game.cover, request),
        "cover_land_url": _asset_url(game.cover_land, request),
        "image_specs": IMAGE_SPECS,
        "error": error,
        "published": game.status == OtomeGame.STATUS_PUBLISHED,
        "asset_rows": _asset_rows(request, _assets_for_game(game)),
        "videos": _assets_for_game(game, OtomeAsset.TYPE_VIDEO),
        "gallery_items": game.gallery_items.filter(is_deleted=False).select_related("asset", "unlock_node"),
        "tab": tab,
    })


@panel_required
def assets_view(request):
    error = ""
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "delete":
                asset = OtomeAsset.objects.get(id=_fk(request.POST.get("asset_id")), is_deleted=False)
                asset.is_deleted = True
                asset.save(update_fields=["is_deleted", "updated_at"])
            elif action == "url":
                _save_url_asset(request)
            elif action == "upload":
                error = _save_upload(request) or ""
            else:
                error = "无法识别的操作"
        except OtomeAsset.DoesNotExist:
            error = "素材不存在"
        except ValueError as exc:
            error = str(exc)
        except Exception:
            logger.error("保存素材失败", exc_info=True)
            error = "保存素材失败"
        if not error:
            return redirect("/otome-admin/assets/")
    rows = []
    for asset in OtomeAsset.objects.filter(is_deleted=False).order_by("-id"):
        rows.append({
            "obj": asset,
            "file_url": _asset_url(asset, request),
            "type_label": _asset_type_label(asset),
            "spec_note": _asset_spec_note(asset),
        })
    return render(request, "otome/assets.html", {
        "assets": rows,
        "error": error,
        "image_specs": IMAGE_SPECS,
    })


def _asset_rows(request, queryset):
    rows = []
    for asset in queryset:
        rows.append({
            "obj": asset,
            "file_url": _asset_url(asset, request),
            "type_label": _asset_type_label(asset),
            "spec_note": _asset_spec_note(asset),
        })
    return rows


def _delete_game_asset(request, game):
    asset = OtomeAsset.objects.get(id=_fk(request.POST.get("asset_id")), is_deleted=False)
    _bind_game(asset, game)
    asset.is_deleted = True
    asset.save(update_fields=["is_deleted", "game", "updated_at"])
    logger.info("游戏详情删除素材 id=%s game=%s", asset.id, game.id)


def _save_gallery(request, game):
    kind = request.POST.get("kind") or ""
    if kind not in (OtomeGalleryItem.KIND_VIDEO, OtomeGalleryItem.KIND_PORTRAIT):
        return "请选择视频或立绘"
    asset = OtomeAsset.objects.filter(id=_fk(request.POST.get("asset")), is_deleted=False).first()
    if asset is None:
        return "请选择素材"
    if kind == OtomeGalleryItem.KIND_VIDEO and asset.asset_type != OtomeAsset.TYPE_VIDEO:
        return "视频解锁要选视频素材"
    if kind == OtomeGalleryItem.KIND_PORTRAIT and asset.asset_type != OtomeAsset.TYPE_IMAGE:
        return "立绘解锁要选图片素材"
    _bind_game(asset, game)
    asset.save(update_fields=["game", "updated_at"])
    item_id = _fk(request.POST.get("item_id"))
    if item_id:
        item = OtomeGalleryItem.objects.get(id=item_id, game=game, is_deleted=False)
    else:
        item = OtomeGalleryItem(game=game)
    unlock_id = _fk(request.POST.get("unlock_node"))
    if unlock_id and not game.nodes.filter(id=unlock_id, is_deleted=False).exists():
        return "解锁剧情不属于这部游戏"
    item.kind = kind
    item.asset = asset
    item.title = (request.POST.get("title") or "").strip() or asset.name
    item.unlock_node_id = unlock_id
    item.unlocked_by_default = _checked(request, "unlocked_by_default")
    item.sort_order = int(request.POST.get("sort_order") or 0)
    item.is_deleted = False
    item.save()
    logger.info("保存解锁内容 id=%s game=%s", item.id, game.id)
    return ""


def _save_url_asset(request, game=None):
    name = (request.POST.get("name") or "").strip()
    url = (request.POST.get("url") or "").strip()
    asset_type = request.POST.get("asset_type") or OtomeAsset.TYPE_IMAGE
    if not name or not url:
        raise ValueError("名称和地址必填")
    if asset_type not in (OtomeAsset.TYPE_IMAGE, OtomeAsset.TYPE_AUDIO, OtomeAsset.TYPE_VIDEO):
        raise ValueError("类型不正确")
    asset_id = _fk(request.POST.get("asset_id"))
    if asset_id:
        asset = OtomeAsset.objects.get(id=asset_id, is_deleted=False)
        if asset.file:
            asset.file.delete(save=False)
        asset.file = ""
    else:
        asset = OtomeAsset()
    asset.name = name
    asset.asset_type = asset_type
    asset.url = url
    _bind_game(asset, game)
    _apply_image_slot(asset, request, upload=None)
    asset.save()
    logger.info("面板保存外链素材 id=%s", asset.id)


def _save_upload(request, game=None):
    upload = request.FILES.get("file")
    if upload is None:
        return "请选择文件"
    ext = os.path.splitext(upload.name)[1].lower()[:8]
    asset_type = request.POST.get("asset_type") or ""
    if not asset_type:
        if ext in IMAGE_EXT:
            asset_type = OtomeAsset.TYPE_IMAGE
        elif ext in AUDIO_EXT:
            asset_type = OtomeAsset.TYPE_AUDIO
        elif ext in VIDEO_EXT:
            asset_type = OtomeAsset.TYPE_VIDEO
    if asset_type == OtomeAsset.TYPE_IMAGE and ext not in IMAGE_EXT:
        return "图片只支持 jpg、png、webp、gif、svg"
    if asset_type == OtomeAsset.TYPE_AUDIO and ext not in AUDIO_EXT:
        return "音频只支持 mp3、wav、m4a、aac、ogg"
    if asset_type == OtomeAsset.TYPE_VIDEO and ext not in VIDEO_EXT:
        return "视频只支持 mp4、webm、mov"
    if asset_type not in (OtomeAsset.TYPE_IMAGE, OtomeAsset.TYPE_AUDIO, OtomeAsset.TYPE_VIDEO):
        return "请选择图片、音频或视频"
    limit = 80 * 1024 * 1024 if asset_type == OtomeAsset.TYPE_VIDEO else 20 * 1024 * 1024
    if upload.size > limit:
        return "视频不能超过 80MB" if asset_type == OtomeAsset.TYPE_VIDEO else "文件不能超过 20MB"
    name = (request.POST.get("name") or "").strip() or upload.name
    asset_id = _fk(request.POST.get("asset_id"))
    if asset_id:
        asset = OtomeAsset.objects.get(id=asset_id, is_deleted=False)
        if asset.file:
            asset.file.delete(save=False)
        asset.file = None
    else:
        asset = OtomeAsset()
    asset.name = name
    asset.asset_type = asset_type
    _bind_game(asset, game)
    _apply_image_slot(asset, request, upload=upload if asset_type == OtomeAsset.TYPE_IMAGE else None)
    try:
        asset.url = store_upload(upload, ext)
    except Exception as exc:
        logger.error("上传到 MinIO 失败", exc_info=True)
        return f"上传到文件存储失败：{exc}"
    apply_upload_meta(asset, upload, request.POST)
    asset.is_deleted = False
    asset.save()
    logger.info("面板上传素材 id=%s", asset.id)
    return ""


@panel_required
def node_edit(request, game_id, node_id=None):
    game = _game_or_404(game_id)
    node = None
    if node_id:
        try:
            node = OtomeNode.objects.get(id=node_id, game=game, is_deleted=False)
        except OtomeNode.DoesNotExist:
            raise Http404("剧情不存在")
    error = request.GET.get("error", "")
    tab = _clean_tab(request.POST.get("stay_tab") or request.GET.get("tab"), NODE_TABS, "line")
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "delete" and node:
                node.is_deleted = True
                node.is_start = False
                node.save(update_fields=["is_deleted", "is_start", "updated_at"])
                node.choices.all().delete()
                OtomeChoice.objects.filter(next_node=node).delete()
                OtomeNode.objects.filter(next_node=node).update(next_node=None)
                return redirect(f"/otome-admin/games/{game.id}/?tab=plot")
            node, error = _save_node(request, game, node)
            if node and node.pk and not error:
                return redirect(f"/otome-admin/games/{game.id}/nodes/{node.id}/?tab={tab}")
            if node and node.pk and error:
                from urllib.parse import quote
                return redirect(f"/otome-admin/games/{game.id}/nodes/{node.id}/?error={quote(error)}&tab={tab}")
        except Exception:
            logger.error("保存剧情失败", exc_info=True)
            error = error or "保存失败"
    images = _assets_for_game(game, OtomeAsset.TYPE_IMAGE)
    videos = _assets_for_game(game, OtomeAsset.TYPE_VIDEO)
    audios = _assets_for_game(game, OtomeAsset.TYPE_AUDIO)
    characters = game.characters.filter(is_deleted=False).order_by("sort_order", "id")
    nodes = game.nodes.filter(is_deleted=False).order_by("sort_order", "id")
    choices = node.choices.all() if node else []
    return render(request, "otome/node.html", {
        "game": game,
        "node": node,
        "images": images,
        "videos": videos,
        "audios": audios,
        "characters": characters,
        "nodes": nodes,
        "choices": choices,
        "error": error,
        "tab": tab,
        "image_specs": IMAGE_SPECS,
    })


def _save_node(request, game, node):
    content = (request.POST.get("content") or "").strip()
    node_key = (request.POST.get("node_key") or "").strip()
    if not content:
        return node, "对白不能为空"
    if not node_key:
        return node, "请填写剧情编号"
    if node is None:
        node = OtomeNode(game=game)
    duplicated = OtomeNode.objects.filter(game=game, node_key=node_key, is_deleted=False)
    if node.pk:
        duplicated = duplicated.exclude(pk=node.pk)
    if duplicated.exists():
        return node, "剧情编号重复"
    node.node_key = node_key
    node.sort_order = int(request.POST.get("sort_order") or 0)
    node.character_id = _fk(request.POST.get("character"))
    node.speaker_name = (request.POST.get("speaker_name") or "").strip()
    node.content = content
    node.background_id = _fk(request.POST.get("background"))
    node.background_land_id = _fk(request.POST.get("background_land"))
    node.portrait_id = _fk(request.POST.get("portrait"))
    node.portrait_land_id = _fk(request.POST.get("portrait_land"))
    node.bgm_id = _fk(request.POST.get("bgm"))
    node.voice_id = _fk(request.POST.get("voice"))
    node.interact_id = _fk(request.POST.get("interact"))
    insert_id = _fk(request.POST.get("insert_media"))
    insert_asset = None
    if insert_id:
        insert_asset = OtomeAsset.objects.filter(id=insert_id, is_deleted=False).first()
        if insert_asset is None or insert_asset.asset_type not in (OtomeAsset.TYPE_IMAGE, OtomeAsset.TYPE_VIDEO):
            return node, "插入内容必须是图片或视频"
        if insert_asset.game_id not in (None, game.id):
            return node, "插入内容属于别的游戏"
    node.insert_media = insert_asset
    node.insert_title = (request.POST.get("insert_title") or "").strip()[:100]
    node.next_node_id = _fk(request.POST.get("next_node"))
    node.is_start = _checked(request, "is_start")
    node.is_key = _checked(request, "is_key")
    node.is_ending = _checked(request, "is_ending")
    node.ending_title = (request.POST.get("ending_title") or "").strip()
    if node.next_node_id and node.next_node_id == node.pk:
        return node, "下一句不能指向自己"
    node.save()
    sync_insert_gallery(node)
    if node.is_start:
        OtomeNode.objects.filter(game=game, is_start=True).exclude(pk=node.pk).update(is_start=False)
    try:
        _save_choices(request, game, node)
    except ValueError as exc:
        return node, str(exc)
    logger.info("面板保存剧情 id=%s key=%s", node.id, node.node_key)
    return node, ""


def _save_choices(request, game, node):
    ids = request.POST.getlist("choice_id")
    texts = request.POST.getlist("choice_text")
    targets = request.POST.getlist("choice_next")
    sounds = request.POST.getlist("choice_interact")
    kept = []
    for index, text in enumerate(texts):
        text = (text or "").strip()
        raw_id = ids[index] if index < len(ids) else ""
        raw_next = targets[index] if index < len(targets) else ""
        raw_sound = sounds[index] if index < len(sounds) else ""
        choice_id = _fk(raw_id)
        next_id = _fk(raw_next)
        interact_id = _fk(raw_sound)
        if not text:
            if choice_id:
                OtomeChoice.objects.filter(id=choice_id, node=node).delete()
            continue
        if not next_id:
            raise ValueError("选项必须选择跳转剧情")
        target = OtomeNode.objects.filter(id=next_id, game=game, is_deleted=False).first()
        if target is None:
            raise ValueError("选项跳转到了别的故事")
        if choice_id:
            choice = OtomeChoice.objects.get(id=choice_id, node=node)
        else:
            choice = OtomeChoice(node=node)
        choice.text = text
        choice.next_node = target
        choice.interact_id = interact_id
        choice.sort_order = index
        choice.save()
        kept.append(choice.id)
    node.choices.exclude(id__in=kept).delete()


def _selected_game(request):
    raw = request.GET.get("game") or ""
    if not raw.isdigit():
        return None
    return OtomeGame.objects.filter(id=int(raw), is_deleted=False).first()


def _page_query(request, drop_page=False):
    data = request.GET.copy()
    if drop_page:
        data.pop("page", None)
    encoded = data.urlencode()
    return f"?{encoded}" if encoded else ""


@panel_required
def data_list(request):
    game = _selected_game(request)
    kind = request.GET.get("kind") or ""
    keyword = (request.GET.get("q") or "").strip()
    queryset = OtomeDataRecord.objects.select_related("player", "game").order_by("-id")
    if game is not None:
        queryset = queryset.filter(game=game)
    if kind in DATA_KIND_LABEL:
        queryset = queryset.filter(kind=kind)
    if keyword:
        queryset = queryset.filter(
            Q(player__uid__icontains=keyword)
            | Q(title__icontains=keyword)
            | Q(detail__icontains=keyword)
            | Q(player__email__icontains=keyword)
        )
    paginator = Paginator(queryset, 30)
    page = paginator.get_page(request.GET.get("page") or 1)
    rows = []
    for item in page.object_list:
        rows.append({
            "created_at": item.created_at,
            "game_title": item.game.title,
            "kind_label": DATA_KIND_LABEL.get(item.kind, item.kind),
            "uid": item.player.uid,
            "title": item.title,
            "detail": item.detail,
        })
    return render(request, "otome/data.html", {
        "rows": rows,
        "page": page,
        "games": OtomeGame.objects.filter(is_deleted=False).order_by("sort_order", "-id"),
        "kinds": OtomeDataRecord.KIND_CHOICES,
        "selected_game": game.id if game else "",
        "selected_kind": kind,
        "keyword": keyword,
        "query": _page_query(request, drop_page=True),
    })


@panel_required
def user_list(request):
    if request.method == "POST":
        error = _save_user_tags(request)
        target = request.get_full_path() or "/otome-admin/users/"
        if error:
            joiner = "&" if "?" in target else "?"
            target = f"{target}{joiner}error={quote(error)}"
        return redirect(target)
    game = _selected_game(request)
    side = request.GET.get("side") or ""
    keyword = (request.GET.get("q") or "").strip()
    games = list(OtomeGame.objects.filter(is_deleted=False).order_by("sort_order", "-id"))
    frontend = []
    backend = []
    if side != "backend":
        players = OtomePlayer.objects.select_related("channel").prefetch_related("game_links__game").order_by("-id")
        if game is not None:
            players = players.filter(game_links__game=game)
        if keyword:
            players = players.filter(
                Q(uid__icontains=keyword)
                | Q(nickname__icontains=keyword)
                | Q(email__icontains=keyword)
                | Q(device_id__icontains=keyword)
            )
        for player in players.distinct():
            tags = [link.game for link in player.game_links.all() if not link.game.is_deleted]
            frontend.append({
                "id": player.id,
                "uid": player.uid,
                "name": player.nickname or player.uid,
                "email": player.email,
                "login_label": "Google" if player.login_type == OtomePlayer.LOGIN_GOOGLE else "设备快速登录",
                "channel_id": player.channel.channel_id if player.channel_id and not player.channel.is_deleted else "",
                "channel_name": player.channel.name if player.channel_id and not player.channel.is_deleted else "",
                "game_ids": [item.id for item in tags],
                "tags": tags,
            })
    if side != "frontend":
        users = User.objects.prefetch_related("game_tags__game").order_by("-id")
        if game is not None:
            users = users.filter(game_tags__game=game)
        if keyword:
            users = users.filter(Q(username__icontains=keyword) | Q(email__icontains=keyword))
        for user in users.distinct():
            tags = [link.game for link in user.game_tags.all() if not link.game.is_deleted]
            backend.append({
                "id": user.id,
                "name": user.username,
                "email": user.email,
                "role": user.role,
                "game_ids": [item.id for item in tags],
                "tags": tags,
            })
    return render(request, "otome/users.html", {
        "frontend": frontend,
        "backend": backend,
        "games": games,
        "selected_game": game.id if game else "",
        "selected_side": side,
        "keyword": keyword,
        "error": request.GET.get("error", ""),
    })


def _save_user_tags(request):
    if request.POST.get("action") != "tags":
        return "无法识别的操作"
    game_ids = []
    for raw in request.POST.getlist("games"):
        if str(raw).isdigit():
            game_ids.append(int(raw))
    games = list(OtomeGame.objects.filter(id__in=game_ids, is_deleted=False))
    owner_id = _fk(request.POST.get("owner_id"))
    side = request.POST.get("side")
    try:
        if side == "frontend":
            player = OtomePlayer.objects.get(id=owner_id)
            OtomePlayerGame.objects.filter(player=player).exclude(game__in=games).delete()
            for item in games:
                OtomePlayerGame.objects.get_or_create(player=player, game=item)
            logger.info("更新前端用户游戏标签 uid=%s", player.uid)
            return ""
        if side == "backend":
            user = User.objects.get(id=owner_id)
            OtomeStaffGame.objects.filter(user=user).exclude(game__in=games).delete()
            for item in games:
                OtomeStaffGame.objects.get_or_create(user=user, game=item)
            logger.info("更新后台用户游戏标签 user=%s", user.username)
            return ""
    except (OtomePlayer.DoesNotExist, User.DoesNotExist):
        return "用户不存在"
    except Exception:
        logger.error("保存用户游戏标签失败", exc_info=True)
        return "保存标签失败"
    return "无法识别的用户类型"


@panel_required
def ads_view(request):
    if request.method == "POST":
        error = _save_ads(request)
        target = "/otome-admin/ads/"
        game = request.POST.get("filter_game") or ""
        if game.isdigit():
            target = f"{target}?game={game}"
        if error:
            joiner = "&" if "?" in target else "?"
            target = f"{target}{joiner}error={quote(error)}"
        return redirect(target)
    game = _selected_game(request)
    channels = OtomeAdChannel.objects.filter(is_deleted=False).select_related("game").order_by("-id")
    builtins = OtomeBuiltinAd.objects.filter(is_deleted=False).select_related("game", "image").order_by("sort_order", "-id")
    if game is not None:
        channels = channels.filter(game=game)
        builtins = builtins.filter(game=game)
    channel_rows = list(channels[:300])
    users, logins, _visits = channel_stats(channel_rows)
    return render(request, "otome/ads.html", {
        "channels": [serialize_channel(item, users, logins, request) for item in channel_rows],
        "builtins": list(builtins[:300]),
        "games": OtomeGame.objects.filter(is_deleted=False).order_by("sort_order", "-id"),
        "slots": OtomeBuiltinAd.SLOT_CHOICES,
        "selected_game": game.id if game else "",
        "error": request.GET.get("error", ""),
    })


def _save_ads(request):
    action = request.POST.get("action") or ""
    try:
        if action == "create_channel":
            name = (request.POST.get("name") or "").strip()[:100]
            game = _selected_post_game(request)
            if not name:
                return "请填写来源名称"
            if game is None:
                return "请选择对应游戏"
            item = OtomeAdChannel.objects.create(
                channel_id=new_channel_id(),
                name=name,
                game=game,
                remark=(request.POST.get("remark") or "").strip()[:200],
            )
            logger.info("面板创建用户来源 channel=%s", item.channel_id)
            return ""
        if action == "toggle_channel":
            item = OtomeAdChannel.objects.get(id=_fk(request.POST.get("id")), is_deleted=False)
            item.status = OtomeAdChannel.STATUS_OFF if item.status == OtomeAdChannel.STATUS_ON else OtomeAdChannel.STATUS_ON
            item.save(update_fields=["status", "updated_at"])
            return ""
        if action == "delete_channel":
            item = OtomeAdChannel.objects.get(id=_fk(request.POST.get("id")), is_deleted=False)
            item.is_deleted = True
            item.status = OtomeAdChannel.STATUS_OFF
            item.save(update_fields=["is_deleted", "status", "updated_at"])
            logger.info("面板删除用户来源 channel=%s", item.channel_id)
            return ""
        if action == "create_builtin":
            title = (request.POST.get("title") or "").strip()[:100]
            game = _selected_post_game(request)
            slot = (request.POST.get("slot") or "").strip()
            if not title:
                return "请填写广告标题"
            if game is None:
                return "请选择对应游戏"
            if slot not in dict(OtomeBuiltinAd.SLOT_CHOICES):
                return "请选择广告位置"
            OtomeBuiltinAd.objects.create(
                game=game,
                title=title,
                slot=slot,
                media_url=(request.POST.get("media_url") or "").strip()[:1000],
                link_url=(request.POST.get("link_url") or "").strip()[:1000],
            )
            logger.info("面板创建内置广告 game=%s", game.id)
            return ""
        if action == "toggle_builtin":
            item = OtomeBuiltinAd.objects.get(id=_fk(request.POST.get("id")), is_deleted=False)
            item.status = OtomeBuiltinAd.STATUS_OFF if item.status == OtomeBuiltinAd.STATUS_ON else OtomeBuiltinAd.STATUS_ON
            item.save(update_fields=["status", "updated_at"])
            return ""
        if action == "delete_builtin":
            item = OtomeBuiltinAd.objects.get(id=_fk(request.POST.get("id")), is_deleted=False)
            item.is_deleted = True
            item.status = OtomeBuiltinAd.STATUS_OFF
            item.save(update_fields=["is_deleted", "status", "updated_at"])
            return ""
    except (OtomeAdChannel.DoesNotExist, OtomeBuiltinAd.DoesNotExist):
        return "记录不存在"
    except Exception:
        logger.error("保存广告失败", exc_info=True)
        return "保存失败"
    return "无法识别的操作"


def _selected_post_game(request):
    raw = request.POST.get("game") or ""
    if not str(raw).isdigit():
        return None
    return OtomeGame.objects.filter(id=int(raw), is_deleted=False).first()
