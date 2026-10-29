import json
import logging
import secrets
import urllib.parse
import urllib.request

from django.conf import settings
from django.core import signing
from rest_framework.views import APIView

from Apps.views.Otome.ads import find_channel, remember_channel
from Apps.views.Otome.content_i18n import field_text, prefer_lang
from Apps.views.Otome.landing import claim_click
from Apps.views.Otome.script import resolve_asset_url
from models.models import (
    OtomeDataRecord,
    OtomeGalleryItem,
    OtomeGame,
    OtomeNode,
    OtomePlayer,
    OtomePlayerGame,
    OtomeSave,
    OtomeUnlock,
)
from tools.utils import ApiResponse

logger = logging.getLogger(__name__)

SALT = "otome-player"
TOKEN_AGE = 60 * 60 * 24 * 30


def _new_uid():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(8):
        uid = "U" + "".join(secrets.choice(alphabet) for _ in range(7))
        if not OtomePlayer.objects.filter(uid=uid).exists():
            return uid
    return "U" + secrets.token_hex(4).upper()


def _game(game_id):
    try:
        return OtomeGame.objects.get(id=int(game_id), is_deleted=False)
    except (OtomeGame.DoesNotExist, TypeError, ValueError):
        return None


def _player_from_request(request):
    token = request.headers.get("token") or request.META.get("HTTP_TOKEN") or ""
    if not token:
        return None
    try:
        data = signing.loads(token, salt=SALT, max_age=TOKEN_AGE)
    except Exception:
        return None
    try:
        return OtomePlayer.objects.get(id=data.get("pid"))
    except OtomePlayer.DoesNotExist:
        return None


def _issue(player):
    token = signing.dumps({"pid": player.id}, salt=SALT)
    from Apps.views.Otome.i18n import tr

    label = "Google" if player.login_type == OtomePlayer.LOGIN_GOOGLE else tr("设备快速登录")
    return {
        "token": token,
        "uid": player.uid,
        "nickname": player.nickname,
        "email": player.email,
        "login_type": player.login_type,
        "login_label": label,
    }


def _touch_game(player, game):
    OtomePlayerGame.objects.get_or_create(player=player, game=game)


def _remember_player_lang(player, request):
    from Apps.views.Otome.i18n import clean_lang, current_lang

    raw = request.data.get("lang")
    code = clean_lang(raw) if str(raw or "").strip() else (current_lang() or "zh-Hans")
    if not code:
        code = current_lang() or "zh-Hans"
    if player.lang == code:
        return
    player.lang = code
    player.save(update_fields=["lang", "updated_at"])


def _log(player, game, kind, title, detail=""):
    OtomeDataRecord.objects.create(
        player=player,
        game=game,
        kind=kind,
        title=title[:120],
        detail=(detail or "")[:300],
        lang=player.lang or "zh-Hans",
    )
    logger.info("乙游数据 kind=%s uid=%s game=%s", kind, player.uid, game.id)


def _save_fields(node):
    if node.speaker_name:
        speaker = field_text(node, "speaker_name")
    elif node.character_id and node.character:
        speaker = field_text(node.character, "name")
    else:
        speaker = node.node_key
    return {
        "node": node,
        "node_key": node.node_key,
        "title": speaker[:100],
        "excerpt": field_text(node, "content")[:200],
    }


def _node_shows_asset(node, asset_id):
    if not asset_id:
        return False
    linked = {
        node.portrait_id,
        node.portrait_land_id,
        node.background_id,
        node.background_land_id,
    }
    character = node.character
    if character is not None:
        linked.add(character.portrait_id)
        linked.add(character.portrait_land_id)
    return asset_id in linked


def _sync_unlocks(player, game, node, insert_seen=False):
    fresh = []
    items = OtomeGalleryItem.objects.filter(game=game, is_deleted=False).select_related("asset")
    for item in items:
        if item.is_insert:
            hit = bool(insert_seen) and item.unlock_node_id == node.id
        elif item.unlocked_by_default:
            hit = True
        elif item.unlock_node_id and item.unlock_node_id == node.id:
            hit = True
        else:
            hit = _node_shows_asset(node, item.asset_id)
        if not hit:
            continue
        _, created = OtomeUnlock.objects.get_or_create(player=player, item=item)
        if created:
            title = field_text(item, "title")
            fresh.append({"id": item.id, "title": title, "kind": item.kind})
            _log(player, game, OtomeDataRecord.KIND_UNLOCK, title, item.get_kind_display())
    return fresh


def _node_for(game, node_id):
    try:
        return OtomeNode.objects.select_related("character").get(id=int(node_id), game=game, is_deleted=False)
    except (OtomeNode.DoesNotExist, TypeError, ValueError):
        return None


def _serialize_save(item):
    return {
        "id": item.id,
        "node_id": item.node_id,
        "node_key": item.node_key,
        "title": field_text(item, "title"),
        "excerpt": item.excerpt,
        "is_auto": item.is_auto,
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }


class PlayConfigView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return ApiResponse(data={
            "google_client_id": getattr(settings, "GOOGLE_CLIENT_ID", "") or "",
        })


class DeviceLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        device_id = str(request.data.get("device_id") or "").strip()[:128]
        game = _game(request.data.get("game_id"))
        if len(device_id) < 6:
            return ApiResponse(message="设备号无效", code=400)
        if game is None:
            return ApiResponse(message="游戏不存在", code=404)
        try:
            player = OtomePlayer.objects.filter(device_id=device_id, game_links__game=game).first()
            if player is None:
                player = OtomePlayer.objects.create(
                    uid=_new_uid(),
                    device_id=device_id,
                    login_type=OtomePlayer.LOGIN_DEVICE,
                )
                logger.info("按设备号创建玩家 uid=%s", player.uid)
            _remember_player_lang(player, request)
            _touch_game(player, game)
            remember_channel(player, find_channel(request.data.get("channel_id"), game))
            claim_click(player, game, request, request.data.get("click_id"))
            _log(player, game, OtomeDataRecord.KIND_LOGIN, "设备快速登录", player.uid)
            return ApiResponse(data=_issue(player), message="登录成功")
        except Exception:
            logger.error("设备登录失败", exc_info=True)
            return ApiResponse(message="登录失败", code=500)


def _verify_google(credential):
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "") or ""
    if not client_id:
        raise ValueError("请先配置 GOOGLE_CLIENT_ID")
    if not credential:
        raise ValueError("缺少 Google 凭证")
    url = "https://oauth2.googleapis.com/tokeninfo?id_token=" + urllib.parse.quote(credential)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        logger.error("校验 Google 登录失败", exc_info=True)
        raise ValueError("Google 登录校验失败")
    if payload.get("aud") != client_id:
        raise ValueError("Google 客户端不匹配")
    if str(payload.get("email_verified")).lower() not in ("true", "1"):
        raise ValueError("Google 邮箱未验证")
    if not payload.get("sub"):
        raise ValueError("Google 账号无效")
    return payload


class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        game = _game(request.data.get("game_id"))
        if game is None:
            return ApiResponse(message="游戏不存在", code=404)
        device_id = str(request.data.get("device_id") or "").strip()[:128]
        try:
            payload = _verify_google(str(request.data.get("credential") or "").strip())
            sub = payload["sub"]
            player = OtomePlayer.objects.filter(google_sub=sub, game_links__game=game).first()
            if player is None and device_id:
                player = OtomePlayer.objects.filter(
                    device_id=device_id, google_sub="", game_links__game=game
                ).first()
            if player is None:
                player = OtomePlayer(uid=_new_uid(), login_type=OtomePlayer.LOGIN_GOOGLE)
            player.google_sub = sub
            player.login_type = OtomePlayer.LOGIN_GOOGLE
            player.email = (payload.get("email") or player.email or "")[:254]
            player.nickname = (payload.get("name") or player.nickname or "")[:64]
            if player.pk is None:
                player.save()
            if device_id:
                OtomePlayer.objects.filter(
                    device_id=device_id, game_links__game=game
                ).exclude(pk=player.pk).update(device_id="")
                player.device_id = device_id
            player.save()
            _remember_player_lang(player, request)
            _touch_game(player, game)
            remember_channel(player, find_channel(request.data.get("channel_id"), game))
            claim_click(player, game, request, request.data.get("click_id"))
            _log(player, game, OtomeDataRecord.KIND_LOGIN, "Google 登录", player.email or player.uid)
            logger.info("Google 登录 uid=%s", player.uid)
            return ApiResponse(data=_issue(player), message="登录成功")
        except ValueError as exc:
            return ApiResponse(message=str(exc), code=400)
        except Exception:
            logger.error("Google 登录失败", exc_info=True)
            return ApiResponse(message="登录失败", code=500)


class PlayerMeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        player = _player_from_request(request)
        if player is None:
            return ApiResponse(message="请先登录", code=401)
        return ApiResponse(data=_issue(player))


class SaveListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, game_id):
        player = _player_from_request(request)
        game = _game(game_id)
        if player is None:
            return ApiResponse(message="请先登录", code=401)
        if game is None:
            return ApiResponse(message="游戏不存在", code=404)
        rows = OtomeSave.objects.filter(player=player, game=game).order_by("-updated_at", "-id")
        return ApiResponse(data={"saves": [_serialize_save(item) for item in rows]})

    def post(self, request, game_id):
        player = _player_from_request(request)
        game = _game(game_id)
        if player is None:
            return ApiResponse(message="请先登录", code=401)
        if game is None:
            return ApiResponse(message="游戏不存在", code=404)
        node = _node_for(game, request.data.get("node_id"))
        if node is None:
            return ApiResponse(message="剧情不存在", code=404)
        try:
            fields = _save_fields(node)
            item = OtomeSave.objects.create(player=player, game=game, is_auto=False, **fields)
            _touch_game(player, game)
            _log(player, game, OtomeDataRecord.KIND_SAVE, fields["title"], fields["excerpt"])
            return ApiResponse(data=_serialize_save(item), message="已存档")
        except Exception:
            logger.error("手动存档失败", exc_info=True)
            return ApiResponse(message="存档失败", code=500)


class SaveDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request, game_id, save_id):
        player = _player_from_request(request)
        if player is None:
            return ApiResponse(message="请先登录", code=401)
        deleted, _ = OtomeSave.objects.filter(id=save_id, player=player, game_id=game_id).delete()
        if not deleted:
            return ApiResponse(message="存档不存在", code=404)
        return ApiResponse(message="已删除")


class GalleryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, game_id):
        player = _player_from_request(request)
        game = _game(game_id)
        if player is None:
            return ApiResponse(message="请先登录", code=401)
        if game is None:
            return ApiResponse(message="游戏不存在", code=404)
        unlocked_ids = set(
            OtomeUnlock.objects.filter(player=player, item__game=game).values_list("item_id", flat=True)
        )
        items = []
        queryset = prefer_lang(list(
            game.gallery_items.filter(is_deleted=False).select_related("asset").order_by("sort_order", "id")
        ))
        for item in queryset:
            asset = item.asset if item.asset_id and not item.asset.is_deleted else None
            media = resolve_asset_url(asset, request)
            opened = item.unlocked_by_default or item.id in unlocked_ids
            items.append({
                "id": item.id,
                "kind": item.kind,
                "title": field_text(item, "title"),
                "unlocked": opened,
                "media_url": media,
            })
        return ApiResponse(data={"items": items})


class ProgressView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, game_id):
        player = _player_from_request(request)
        game = _game(game_id)
        if player is None:
            return ApiResponse(message="请先登录", code=401)
        if game is None:
            return ApiResponse(message="游戏不存在", code=404)
        node = _node_for(game, request.data.get("node_id"))
        if node is None:
            return ApiResponse(message="剧情不存在", code=404)
        try:
            fields = _save_fields(node)
            auto = OtomeSave.objects.filter(player=player, game=game, is_auto=True).first()
            changed = auto is None or auto.node_id != node.id
            if auto is None:
                auto = OtomeSave(player=player, game=game, is_auto=True)
            for key, value in fields.items():
                setattr(auto, key, value)
            auto.save()
            _touch_game(player, game)
            if changed:
                _log(player, game, OtomeDataRecord.KIND_PROGRESS, fields["title"], fields["excerpt"])
            seen = request.data.get("insert_seen") in (True, 1, "1", "true", "True")
            fresh = _sync_unlocks(player, game, node, insert_seen=seen)
            return ApiResponse(data={"save": _serialize_save(auto), "newly_unlocked": fresh})
        except Exception:
            logger.error("同步进度失败", exc_info=True)
            return ApiResponse(message="进度保存失败", code=500)
