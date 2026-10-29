import logging
import secrets
from datetime import datetime, timedelta

from django.db import IntegrityError
from django.db.models import Count, F
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from Apps.views.Otome.content_i18n import (
    AD_FIELDS,
    AD_LIMITS,
    CHANNEL_FIELDS,
    CHANNEL_LIMITS,
    clean_texts,
    field_text,
    prefer_lang,
)
from Apps.views.Otome.i18n import clean_lang, filter_lang, lang_name, tr
from Apps.views.Otome.permissions import IsOtomeAdmin, ensure_game_access, sees_all_games, visible_games
from Apps.views.Otome.script import resolve_asset_url
from models.models import (
    OtomeAdChannel,
    OtomeAdClick,
    OtomeAsset,
    OtomeBuiltinAd,
    OtomeBuiltinAdEvent,
    OtomeDataRecord,
    OtomeGame,
    OtomePlayer,
)
from tools.utils import ApiResponse

logger = logging.getLogger(__name__)

SLOT_LABEL = dict(OtomeBuiltinAd.SLOT_CHOICES)


def new_channel_id():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(8):
        code = "C" + "".join(secrets.choice(alphabet) for _ in range(8))
        if not OtomeAdChannel.objects.filter(channel_id=code).exists():
            return code
    return "C" + secrets.token_hex(4).upper()


def _game(raw):
    try:
        return OtomeGame.objects.get(id=int(raw), is_deleted=False)
    except (OtomeGame.DoesNotExist, TypeError, ValueError):
        return None


def _owned_game(request, raw):
    game = _game(raw)
    if game is None:
        return None
    try:
        ensure_game_access(request, game)
    except ValidationError:
        return None
    return game


def _status(raw, default=OtomeAdChannel.STATUS_ON):
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value not in (OtomeAdChannel.STATUS_OFF, OtomeAdChannel.STATUS_ON):
        return None
    return value


def _asset(raw):
    if raw in (None, ""):
        return None
    try:
        return OtomeAsset.objects.get(id=int(raw), is_deleted=False)
    except (OtomeAsset.DoesNotExist, TypeError, ValueError):
        return False


def media_of(ad, request):
    url = (ad.media_url or "").strip()
    kind = "image"
    if ad.image_id and ad.image is not None and not ad.image.is_deleted:
        resolved = resolve_asset_url(ad.image, request)
        if resolved:
            url = resolved
        kind = ad.image.asset_type or "image"
    elif url.lower().split("?", 1)[0].endswith((".mp4", ".webm", ".mov")):
        kind = "video"
    return url, kind


def _parse_bound(raw):
    text = (raw or "").strip()
    if not text:
        return None
    try:
        day = datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    today = timezone.localdate()
    return today if day > today else day


def _request_range(request):
    start = _parse_bound(request.query_params.get("date_from"))
    end = _parse_bound(request.query_params.get("date_to"))
    if start and end and start > end:
        start, end = end, start
    return start, end


def _aware_start(day):
    start = datetime.combine(day, datetime.min.time())
    if timezone.is_naive(start):
        return timezone.make_aware(start, timezone.get_current_timezone())
    return start


def _apply_created_range(queryset, start, end):
    if start:
        queryset = queryset.filter(created_at__gte=_aware_start(start))
    if end:
        queryset = queryset.filter(created_at__lt=_aware_start(end + timedelta(days=1)))
    return queryset


def channel_stats(channels, start=None, end=None):
    """返回新增人数、登录次数，以及按时间筛选时的访问次数。未选时间时访问次数为空，沿用累计值。"""
    ids = [item.id for item in channels]
    users = {}
    logins = {}
    visits = None
    if not ids:
        return users, logins, visits
    user_qs = OtomePlayer.objects.filter(channel_id__in=ids)
    login_qs = OtomeDataRecord.objects.filter(
        kind=OtomeDataRecord.KIND_LOGIN,
        player__channel_id__in=ids,
        created_at__gte=F("player__channel__created_at"),
    )
    if start or end:
        user_qs = _apply_created_range(user_qs, start, end)
        login_qs = _apply_created_range(login_qs, start, end)
        visits = {}
        click_qs = _apply_created_range(OtomeAdClick.objects.filter(channel_id__in=ids), start, end)
        for row in click_qs.values("channel_id").annotate(n=Count("id")):
            visits[row["channel_id"]] = row["n"]
    for row in user_qs.values("channel_id").annotate(n=Count("id")):
        users[row["channel_id"]] = row["n"]
    for row in login_qs.values("player__channel_id", "game_id").annotate(n=Count("id")):
        logins[(row["player__channel_id"], row["game_id"])] = row["n"]
    return users, logins, visits


def serialize_channel(item, users, logins, request=None, visits=None):
    path = f"/go/{item.channel_id}/"
    return {
        "id": item.id,
        "channel_id": item.channel_id,
        "name": item.name,
        "texts": item.texts or {},
        "game_id": item.game_id,
        "game_title": item.game.title,
        "lang": item.lang,
        "lang_label": lang_name(item.lang),
        "remark": item.remark,
        "status": item.status,
        "visit_count": item.visit_count if visits is None else visits.get(item.id, 0),
        "user_count": users.get(item.id, 0),
        "login_count": logins.get((item.id, item.game_id), 0),
        "query": f"ch={item.channel_id}",
        "landing_url": request.build_absolute_uri(path) if request is not None else path,
        "created_at": item.created_at.isoformat() if item.created_at else "",
    }


def builtin_people(ads, start=None, end=None):
    shows = {}
    clicks = {}
    ids = [item.id for item in ads]
    if not ids:
        return shows, clicks
    rows = (
        _apply_created_range(OtomeBuiltinAdEvent.objects.filter(ad_id__in=ids), start, end)
        .values("ad_id", "action")
        .annotate(n=Count("id"))
    )
    for row in rows:
        target = shows if row["action"] == OtomeBuiltinAdEvent.ACTION_SHOW else clicks
        target[row["ad_id"]] = row["n"]
    return shows, clicks


def serialize_builtin(item, request, shows=None, clicks=None):
    url, kind = media_of(item, request)
    shows = shows or {}
    clicks = clicks or {}
    return {
        "id": item.id,
        "game_id": item.game_id,
        "game_title": item.game.title,
        "lang": item.lang,
        "lang_label": lang_name(item.lang),
        "title": item.title,
        "texts": item.texts or {},
        "slot": item.slot,
        "slot_label": tr(SLOT_LABEL.get(item.slot, item.slot)),
        "image_id": item.image_id,
        "media_url": item.media_url,
        "file_url": url,
        "media_kind": kind,
        "link_url": item.link_url,
        "sort_order": item.sort_order,
        "status": item.status,
        "show_people": shows.get(item.id, 0),
        "click_people": clicks.get(item.id, 0),
    }


def record_builtin_event(ad, action, device_id, player):
    device_id = (device_id or "").strip()[:128]
    if not device_id:
        return False
    try:
        event, _created = OtomeBuiltinAdEvent.objects.get_or_create(
            ad=ad,
            action=action,
            device_id=device_id,
            defaults={"player": player},
        )
    except IntegrityError:
        return True
    if player is not None and event.player_id is None:
        event.player = player
        event.save(update_fields=["player"])
    return True


def find_channel(code, game):
    text = (code or "").strip()[:16]
    if not text or game is None:
        return None
    return OtomeAdChannel.objects.filter(
        channel_id=text,
        game=game,
        is_deleted=False,
        status=OtomeAdChannel.STATUS_ON,
    ).first()


def remember_channel(player, channel):
    if player is None or channel is None or player.channel_id:
        return
    player.channel = channel
    player.save(update_fields=["channel", "updated_at"])
    logger.info("玩家归因渠道 uid=%s channel=%s", player.uid, channel.channel_id)


def count_visit(channel):
    if channel is None:
        return
    OtomeAdChannel.objects.filter(id=channel.id).update(visit_count=F("visit_count") + 1)


def retire_ads_for_game(game):
    """游戏软删后，同步下架关联的用户来源和内置广告，避免列表还能点进已失效的统计。"""
    now = timezone.now()
    OtomeAdChannel.objects.filter(game=game, is_deleted=False).update(
        is_deleted=True, status=OtomeAdChannel.STATUS_OFF, updated_at=now,
    )
    OtomeBuiltinAd.objects.filter(game=game, is_deleted=False).update(
        is_deleted=True, status=OtomeBuiltinAd.STATUS_OFF, updated_at=now,
    )


class AdminAdChannelView(APIView):
    permission_classes = [IsOtomeAdmin]

    def get(self, request):
        # 与详情 ensure_game_access 对齐：已删游戏的来源不再出现在列表
        queryset = (
            OtomeAdChannel.objects.filter(is_deleted=False, game__is_deleted=False)
            .select_related("game")
            .order_by("-id")
        )
        if not sees_all_games(request):
            queryset = queryset.filter(game__in=visible_games(request))
        game = _owned_game(request, request.query_params.get("game")) if request.query_params.get("game") else None
        if request.query_params.get("game") and game is None:
            return ApiResponse(data=[])
        if game is not None:
            queryset = queryset.filter(game=game)
        queryset = filter_lang(queryset, request.query_params.get("lang"))
        start, end = _request_range(request)
        queryset = _apply_created_range(queryset, start, end)
        rows = list(queryset[:300])
        users, logins, visits = channel_stats(rows, start, end)
        return ApiResponse(data=[serialize_channel(item, users, logins, request, visits) for item in rows])

    def post(self, request):
        name = str(request.data.get("name") or "").strip()[:100]
        game = _owned_game(request, request.data.get("game") or request.data.get("game_id"))
        if not name:
            return ApiResponse(message="请填写来源名称", code=400)
        if game is None:
            return ApiResponse(message="请选择对应游戏", code=400)
        try:
            lang = clean_lang(request.data.get("lang"))
            if lang is None:
                return ApiResponse(message="请选择语言", code=400)
            try:
                texts = clean_texts(request.data.get("texts"), CHANNEL_FIELDS, CHANNEL_LIMITS, lang)
            except ValueError:
                return ApiResponse(message="多语言格式不正确", code=400)
            item = OtomeAdChannel.objects.create(
                channel_id=new_channel_id(),
                name=name,
                game=game,
                lang=lang,
                texts=texts,
                remark=str(request.data.get("remark") or "").strip()[:200],
            )
            logger.info("创建用户来源 channel=%s game=%s", item.channel_id, game.id)
            users, logins, visits = channel_stats([item])
            return ApiResponse(data=serialize_channel(item, users, logins, request, visits), message="来源已创建")
        except Exception:
            logger.error("创建用户来源失败", exc_info=True)
            return ApiResponse(message="创建来源失败", code=500)


class AdminAdChannelDetailView(APIView):
    permission_classes = [IsOtomeAdmin]

    def get(self, request, channel_pk):
        item = _staff_channel(request, channel_pk)
        if item is None:
            return ApiResponse(message="来源不存在", code=404)
        start, end = _request_range(request)
        users, logins, visits = channel_stats([item], start, end)
        people = []
        players = _apply_created_range(item.players.order_by("-id"), start, end)[:30]
        for player in players:
            people.append({
                "id": player.id,
                "uid": player.uid,
                "name": player.nickname or player.uid,
                "email": player.email,
                "login_label": "Google" if player.login_type == OtomePlayer.LOGIN_GOOGLE else tr("设备快速登录"),
                "created_at": player.created_at.isoformat() if player.created_at else "",
            })
        data = serialize_channel(item, users, logins, request, visits)
        data["players"] = people
        return ApiResponse(data=data)

    def patch(self, request, channel_pk):
        item = _staff_channel(request, channel_pk)
        if item is None:
            return ApiResponse(message="来源不存在", code=404)
        name = str(request.data.get("name") if "name" in request.data else item.name).strip()[:100]
        if not name:
            return ApiResponse(message="请填写来源名称", code=400)
        if "game" in request.data or "game_id" in request.data:
            game = _owned_game(request, request.data.get("game") or request.data.get("game_id"))
            if game is None:
                return ApiResponse(message="请选择对应游戏", code=400)
            item.game = game
        status = _status(request.data.get("status"), item.status) if "status" in request.data else item.status
        if status is None:
            return ApiResponse(message="状态无效", code=400)
        try:
            item.name = name
            item.remark = str(request.data.get("remark") if "remark" in request.data else item.remark).strip()[:200]
            item.status = status
            if "lang" in request.data:
                lang = clean_lang(request.data.get("lang"))
                if lang is None:
                    return ApiResponse(message="请选择语言", code=400)
                item.lang = lang
            if "texts" in request.data:
                try:
                    item.texts = clean_texts(request.data.get("texts"), CHANNEL_FIELDS, CHANNEL_LIMITS, item.lang)
                except ValueError:
                    return ApiResponse(message="多语言格式不正确", code=400)
            item.save()
            logger.info("更新用户来源 channel=%s", item.channel_id)
            users, logins, visits = channel_stats([item])
            return ApiResponse(data=serialize_channel(item, users, logins, request, visits), message="来源已保存")
        except Exception:
            logger.error("更新用户来源失败", exc_info=True)
            return ApiResponse(message="保存来源失败", code=500)

    def delete(self, request, channel_pk):
        item = _staff_channel(request, channel_pk)
        if item is None:
            return ApiResponse(message="来源不存在", code=404)
        item.is_deleted = True
        item.status = OtomeAdChannel.STATUS_OFF
        item.save(update_fields=["is_deleted", "status", "updated_at"])
        logger.info("删除用户来源 channel=%s", item.channel_id)
        return ApiResponse(message="来源已删除")


def _alive_channel(pk):
    try:
        return OtomeAdChannel.objects.select_related("game").get(id=int(pk), is_deleted=False)
    except (OtomeAdChannel.DoesNotExist, TypeError, ValueError):
        return None


def _staff_channel(request, pk):
    item = _alive_channel(pk)
    if item is None:
        return None
    try:
        ensure_game_access(request, item.game)
    except ValidationError:
        return None
    return item


class AdminBuiltinAdView(APIView):
    permission_classes = [IsOtomeAdmin]

    def get(self, request):
        queryset = (
            OtomeBuiltinAd.objects.filter(is_deleted=False, game__is_deleted=False)
            .select_related("game", "image")
            .order_by("sort_order", "-id")
        )
        if not sees_all_games(request):
            queryset = queryset.filter(game__in=visible_games(request))
        if request.query_params.get("game"):
            game = _owned_game(request, request.query_params.get("game"))
            if game is None:
                return ApiResponse(data=[])
            queryset = queryset.filter(game=game)
        queryset = filter_lang(queryset, request.query_params.get("lang"))
        start, end = _request_range(request)
        queryset = _apply_created_range(queryset, start, end)
        rows = list(queryset[:300])
        shows, clicks = builtin_people(rows, start, end)
        return ApiResponse(data=[serialize_builtin(item, request, shows, clicks) for item in rows])

    def post(self, request):
        item, error = _fill_builtin(OtomeBuiltinAd(), request, creating=True)
        if error:
            return ApiResponse(message=error, code=400)
        try:
            item.save()
            logger.info("创建内置广告 id=%s game=%s", item.id, item.game_id)
            item = OtomeBuiltinAd.objects.select_related("game", "image").get(id=item.id)
            shows, clicks = builtin_people([item])
            return ApiResponse(data=serialize_builtin(item, request, shows, clicks), message="广告已创建")
        except Exception:
            logger.error("创建内置广告失败", exc_info=True)
            return ApiResponse(message="创建广告失败", code=500)


class AdminBuiltinAdDetailView(APIView):
    permission_classes = [IsOtomeAdmin]

    def patch(self, request, ad_pk):
        item = _staff_ad(request, ad_pk)
        if item is None:
            return ApiResponse(message="广告不存在", code=404)
        item, error = _fill_builtin(item, request, creating=False)
        if error:
            return ApiResponse(message=error, code=400)
        try:
            item.save()
            logger.info("更新内置广告 id=%s", item.id)
            item = OtomeBuiltinAd.objects.select_related("game", "image").get(id=item.id)
            shows, clicks = builtin_people([item])
            return ApiResponse(data=serialize_builtin(item, request, shows, clicks), message="广告已保存")
        except Exception:
            logger.error("更新内置广告失败", exc_info=True)
            return ApiResponse(message="保存广告失败", code=500)

    def delete(self, request, ad_pk):
        item = _staff_ad(request, ad_pk)
        if item is None:
            return ApiResponse(message="广告不存在", code=404)
        item.is_deleted = True
        item.status = OtomeBuiltinAd.STATUS_OFF
        item.save(update_fields=["is_deleted", "status", "updated_at"])
        logger.info("删除内置广告 id=%s", item.id)
        return ApiResponse(message="广告已删除")


def _alive_ad(pk):
    try:
        return OtomeBuiltinAd.objects.select_related("game", "image").get(id=int(pk), is_deleted=False)
    except (OtomeBuiltinAd.DoesNotExist, TypeError, ValueError):
        return None


def _staff_ad(request, pk):
    item = _alive_ad(pk)
    if item is None:
        return None
    try:
        ensure_game_access(request, item.game)
    except ValidationError:
        return None
    return item


def _fill_builtin(item, request, creating):
    data = request.data
    if creating or "title" in data:
        title = str(data.get("title") or "").strip()[:100]
    else:
        title = item.title
    if not title:
        return item, "请填写广告标题"
    if creating or "game" in data or "game_id" in data:
        game = _owned_game(request, data.get("game") or data.get("game_id"))
        if game is None:
            return item, "请选择对应游戏"
        item.game = game
    if creating or "slot" in data:
        slot = str(data.get("slot") or "").strip()
    else:
        slot = item.slot
    if slot not in SLOT_LABEL:
        return item, "请选择广告位置"
    if creating or "image" in data or "image_id" in data:
        raw_image = data.get("image") if "image" in data else data.get("image_id")
        image = _asset(raw_image)
        if image is False:
            return item, "素材不存在"
        item.image = image
    if "status" in data:
        status = _status(data.get("status"))
        if status is None:
            return item, "状态无效"
    else:
        status = item.status if item.pk else OtomeBuiltinAd.STATUS_ON
    if "sort_order" in data or creating:
        try:
            sort_order = int(data.get("sort_order") or 0)
        except (TypeError, ValueError):
            return item, "排序必须是数字"
    else:
        sort_order = item.sort_order
    if creating or "lang" in data:
        lang = clean_lang(data.get("lang"))
        if lang is None:
            return item, "请选择语言"
        item.lang = lang
    if creating or "texts" in data:
        try:
            item.texts = clean_texts(data.get("texts"), AD_FIELDS, AD_LIMITS, item.lang or "zh-Hans")
        except ValueError:
            return item, "多语言格式不正确"
    item.title = title
    item.slot = slot
    if creating or "media_url" in data:
        item.media_url = str(data.get("media_url") or "").strip()[:1000]
    if creating or "link_url" in data:
        item.link_url = str(data.get("link_url") or "").strip()[:1000]
    item.sort_order = sort_order
    item.status = status
    return item, ""


class PlayAdsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, game_id):
        game = _game(game_id)
        if game is None:
            return ApiResponse(message="游戏不存在", code=404)
        code = request.query_params.get("channel") or request.query_params.get("ch") or ""
        channel = find_channel(code, game)
        if channel is not None:
            count_visit(channel)
            from Apps.views.Otome.player import _player_from_request
            remember_channel(_player_from_request(request), channel)
        ads = prefer_lang(list(
            OtomeBuiltinAd.objects.filter(game=game, is_deleted=False, status=OtomeBuiltinAd.STATUS_ON)
            .select_related("image")
            .order_by("sort_order", "id")
        ))
        rows = []
        for item in ads:
            url, kind = media_of(item, request)
            rows.append({
                "id": item.id,
                "title": field_text(item, "title"),
                "slot": item.slot,
                "media_url": url,
                "media_kind": kind,
                "link_url": item.link_url,
            })
        return ApiResponse(data={"ads": rows})


class PlayAdTrackView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, game_id, ad_id):
        game = _game(game_id)
        if game is None:
            return ApiResponse(message="游戏不存在", code=404)
        ad = OtomeBuiltinAd.objects.filter(id=ad_id, game=game, is_deleted=False).first()
        if ad is None:
            return ApiResponse(message="广告不存在", code=404)
        action = str(request.data.get("action") or "").strip()
        if action not in (OtomeBuiltinAdEvent.ACTION_SHOW, OtomeBuiltinAdEvent.ACTION_CLICK):
            return ApiResponse(message="动作无效", code=400)
        device_id = str(request.data.get("device_id") or "").strip()[:128]
        if not device_id:
            return ApiResponse(message="缺少设备号", code=400)
        from Apps.views.Otome.player import _player_from_request

        record_builtin_event(ad, action, device_id, _player_from_request(request))
        return ApiResponse(message="已记录")
