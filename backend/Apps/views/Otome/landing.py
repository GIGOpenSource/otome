import logging
import re
import secrets
import urllib.parse
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from Apps.views.Otome.ads import count_visit, remember_channel
from Apps.views.Otome.content_i18n import field_text
from Apps.views.Otome.i18n import LANGS, current_lang, lang_meta, tr
from Apps.views.Otome.links import resolve_frontend_url
from Apps.views.Otome.script import resolve_asset_url
from models.models import OtomeAdChannel, OtomeAdClick

logger = logging.getLogger(__name__)

COOKIE = "otome_click"
CLICK_WINDOW = timedelta(hours=48)
PACKAGE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+")


def clean_package(raw):
    text = str(raw or "").strip()[:120]
    if not text:
        return ""
    if not PACKAGE_RE.fullmatch(text):
        return None
    return text


def clean_ios(raw):
    text = str(raw or "").strip()
    if text.lower().startswith("id"):
        text = text[2:]
    text = text[:32]
    if not text:
        return ""
    if not text.isdigit():
        return None
    return text


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.META.get("REMOTE_ADDR") or "")[:64]


def platform_of(user_agent):
    text = (user_agent or "").lower()
    if "android" in text:
        return "android"
    if "iphone" in text or "ipad" in text or "ios" in text:
        return "ios"
    return "other"


def public_channel(code):
    text = (code or "").strip()[:16]
    if not text:
        return None
    return (
        OtomeAdChannel.objects.select_related("game", "game__cover")
        .filter(
            channel_id=text,
            is_deleted=False,
            status=OtomeAdChannel.STATUS_ON,
            game__is_deleted=False,
        )
        .first()
    )


def store_ids(game):
    package = (getattr(game, "play_package", "") or "").strip()
    ios_id = (getattr(game, "ios_app_id", "") or "").strip()
    if not package:
        package = (getattr(settings, "OTOME_PLAY_PACKAGE", "") or "").strip()
    if not ios_id:
        ios_id = (getattr(settings, "OTOME_IOS_APP_ID", "") or "").strip()
    return package, ios_id


def store_url(game, store, click_id="", channel_id=""):
    package, ios_id = store_ids(game)
    if store == "google":
        if not package:
            return ""
        query = {"id": package}
        if click_id and channel_id:
            query["referrer"] = urllib.parse.urlencode({"click_id": click_id, "ch": channel_id})
        return "https://play.google.com/store/apps/details?" + urllib.parse.urlencode(query)
    if store == "ios":
        if not ios_id.isdigit():
            return ""
        if channel_id:
            return f"https://apps.apple.com/app/id{ios_id}?ct={urllib.parse.quote(channel_id)}&mt=8"
        return f"https://apps.apple.com/app/id{ios_id}"
    return ""


def _new_click_id():
    for _ in range(8):
        code = secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:16]
        if code and not OtomeAdClick.objects.filter(click_id=code).exists():
            return code
    return secrets.token_hex(8)


def ensure_click(request, channel):
    token = (request.COOKIES.get(COOKIE) or "")[:32]
    if token:
        found = OtomeAdClick.objects.filter(click_id=token, channel=channel, player__isnull=True).first()
        if found is not None:
            return found, False
    agent = (request.META.get("HTTP_USER_AGENT") or "")[:300]
    click = OtomeAdClick.objects.create(
        click_id=_new_click_id(),
        channel=channel,
        ip=client_ip(request),
        user_agent=agent,
        platform=platform_of(agent),
    )
    count_visit(channel)
    logger.info("落地页访问 channel=%s click=%s", channel.channel_id, click.click_id)
    return click, True


def _remember_cookie(response, click):
    response.set_cookie(
        COOKIE,
        click.click_id,
        max_age=14 * 24 * 3600,
        samesite="Lax",
        httponly=True,
    )
    return response


def _public_game(game_id):
    from models.models import OtomeGame

    return OtomeGame.objects.filter(id=game_id, is_deleted=False).first()


def _page(request, channel, click, missing=""):
    context = _landing_context(request, channel.game, missing, click.platform if click else "")
    context["download_base"] = f"/go/{channel.channel_id}"
    context["tracked"] = True
    context["ui"] = _landing_ui(True)
    return context


def _landing_context(request, game, missing="", prefer=""):
    cover = game.cover if game.cover_id and game.cover is not None and not game.cover.is_deleted else None
    package, ios_id = store_ids(game)
    return {
        "game": game,
        "cover_url": resolve_asset_url(cover, request),
        "cover_kind": cover.asset_type if cover is not None else "",
        "title": field_text(game, "title"),
        "subtitle": field_text(game, "subtitle"),
        "summary": field_text(game, "summary").strip(),
        "google_ready": bool(package),
        "ios_ready": bool(ios_id) and ios_id.isdigit(),
        "prefer": prefer,
        "missing": missing,
        "play_url": resolve_frontend_url(game),
        "download_base": f"/land/{game.id}",
        "tracked": False,
        "ui": _landing_ui(False),
    }


def _landing_ui(tracked):
    meta = lang_meta()
    return {
        "lang": current_lang(),
        "dir": meta["dir"],
        "langs": LANGS,
        "language": tr("语言"),
        "google": tr("Google Play 下载"),
        "ios": tr("App Store 下载"),
        "store_note": tr("下载后打开，会记住这次来源") if tracked else tr("下载安装包"),
        "missing": tr("下载地址还没配置"),
        "enter": tr("进入游戏"),
        "enter_note": tr("直接打开，和这个下载页不是同一个地址"),
        "tracked_note": tr("这次访问已经记下。安装并打开游戏后，会和这台设备对上，用来识别广告来源。进入游戏会打开另一个地址。"),
        "plain_note": tr("这是下载页。进入游戏会打开另一个地址。"),
    }


def landing_page(request, channel_id):
    channel = public_channel(channel_id)
    if channel is None:
        return HttpResponse(tr("这条来源不存在或已停用。"), status=404, content_type="text/plain; charset=utf-8")
    click, _created = ensure_click(request, channel)
    response = render(request, "otome/landing.html", _page(request, channel, click))
    return _remember_cookie(response, click)


def landing_download(request, channel_id, store):
    if store not in ("google", "ios"):
        return HttpResponse(tr("下载地址无效。"), status=404, content_type="text/plain; charset=utf-8")
    channel = public_channel(channel_id)
    if channel is None:
        return HttpResponse(tr("这条来源不存在或已停用。"), status=404, content_type="text/plain; charset=utf-8")
    click, _created = ensure_click(request, channel)
    chosen = "android" if store == "google" else "ios"
    if click.platform != chosen:
        click.platform = chosen
        click.save(update_fields=["platform"])
    target = store_url(channel.game, store, click.click_id, channel.channel_id)
    if not target:
        missing = "Google Play" if store == "google" else "App Store"
        response = render(request, "otome/landing.html", _page(request, channel, click, missing))
        return _remember_cookie(response, click)
    logger.info("落地页跳转商店 channel=%s click=%s store=%s", channel.channel_id, click.click_id, store)
    return _remember_cookie(redirect(target), click)


def game_landing(request, game_id):
    """这部游戏自己的下载页。进入游戏是另一个地址。"""
    game = _public_game(game_id)
    if game is None:
        return HttpResponse(tr("故事不存在。"), status=404, content_type="text/plain; charset=utf-8")
    return render(request, "otome/landing.html", _landing_context(request, game))


def game_landing_download(request, game_id, store):
    if store not in ("google", "ios"):
        return HttpResponse(tr("下载地址无效。"), status=404, content_type="text/plain; charset=utf-8")
    game = _public_game(game_id)
    if game is None:
        return HttpResponse(tr("故事不存在。"), status=404, content_type="text/plain; charset=utf-8")
    target = store_url(game, store)
    if not target:
        missing = "Google Play" if store == "google" else "App Store"
        return render(request, "otome/landing.html", _landing_context(request, game, missing))
    return redirect(target)


def _open_clicks(game):
    since = timezone.now() - CLICK_WINDOW
    return OtomeAdClick.objects.filter(
        player__isnull=True,
        created_at__gte=since,
        channel__game=game,
        channel__is_deleted=False,
        channel__status=OtomeAdChannel.STATUS_ON,
    )


def claim_click(player, game, request, click_id=""):
    """打开游戏后，把这次设备和落地页上的访问标记对上。已有来源的玩家不再改。"""
    if player is None or game is None:
        return None
    token = str(click_id or request.COOKIES.get(COOKIE) or "").strip()[:32]
    click = None
    if token:
        click = _open_clicks(game).filter(click_id=token).select_related("channel").first()
    if click is None:
        ip = client_ip(request)
        if ip:
            click = _open_clicks(game).filter(ip=ip).select_related("channel").order_by("-id").first()
    if click is None:
        return None
    if player.channel_id and player.channel_id != click.channel_id:
        return None
    click.player = player
    click.device_id = (player.device_id or "")[:128]
    click.matched_at = timezone.now()
    click.save(update_fields=["player", "device_id", "matched_at"])
    remember_channel(player, click.channel)
    logger.info(
        "落地页归因 uid=%s click=%s channel=%s device=%s",
        player.uid, click.click_id, click.channel.channel_id, click.device_id,
    )
    return click
