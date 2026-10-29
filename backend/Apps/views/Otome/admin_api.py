import csv
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from urllib.parse import quote

from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView

from Apps.views.Otome.permissions import (
    STAFF_ROLES,
    IsOtomeAdmin,
    current_staff,
    issue_staff_token,
    sees_all_games,
    visible_games,
)
from models.models import (
    OtomeAdChannel,
    OtomeAdClick,
    OtomeChoice,
    OtomeDataRecord,
    OtomeGame,
    OtomeNode,
    OtomePlayer,
    OtomePlayerGame,
    OtomeSave,
    OtomeStaffGame,
    User,
)
from Apps.views.Otome.i18n import canonical, clean_lang, filter_lang, lang_name, tr
from tools.password_hasher import verify_password
from tools.utils import ApiResponse

logger = logging.getLogger(__name__)

KIND_LABEL = dict(OtomeDataRecord.KIND_CHOICES)
FUNNEL_STEPS = (
    (0, "注册"),
    (10, "进度 ≥10%"),
    (25, "进度 ≥25%"),
    (50, "进度 ≥50%"),
    (75, "进度 ≥75%"),
    (100, "进度 100%"),
)
RETENTION_OFFSETS = (
    (0, "当日", "d0"),
    (1, "次日", "d1"),
    (2, "2日", "d2"),
    (3, "3日", "d3"),
    (4, "4日", "d4"),
    (5, "5日", "d5"),
    (6, "6日", "d6"),
    (7, "7日", "d7"),
    (14, "14日", "d14"),
    (30, "30日", "d30"),
)
RETENTION_DAYS = 14
RETENTION_SPAN = 90


def story_progress_percents(nodes, choice_edges):
    """每个剧情节点对应的进度百分比。

    有选项时只走选项，否则走下一句，和剧情图一致。
    开场是 0%，任一结局是 100%，中途按「已走步数 / 到最近结局的总步数」折算。
    没有结局时，按从开场到最深处的比例折算，最深处记为 100%。
    """
    nodes = list(nodes)
    if not nodes:
        return {}
    alive = {item["id"] for item in nodes}
    outgoing = defaultdict(list)
    choice_nodes = set()
    for source, target in choice_edges:
        if source in alive and target in alive:
            outgoing[source].append(target)
            choice_nodes.add(source)
    for item in nodes:
        if item["id"] in choice_nodes:
            continue
        target = item["next_node_id"]
        if target in alive:
            outgoing[item["id"]].append(target)

    start = next((item for item in nodes if item["is_start"]), None)
    if start is None:
        start = min(nodes, key=lambda item: (item["sort_order"], item["id"]))

    depth = {start["id"]: 0}
    queue = deque([start["id"]])
    while queue:
        current = queue.popleft()
        for nxt in outgoing[current]:
            if nxt in depth:
                continue
            depth[nxt] = depth[current] + 1
            queue.append(nxt)

    endings = [item["id"] for item in nodes if item["is_ending"]]
    reverse = defaultdict(list)
    for source, targets in outgoing.items():
        for target in targets:
            reverse[target].append(source)
    dist_end = {}
    queue = deque()
    for ending_id in endings:
        if ending_id in dist_end:
            continue
        dist_end[ending_id] = 0
        queue.append(ending_id)
    while queue:
        current = queue.popleft()
        for prev in reverse[current]:
            if prev in dist_end:
                continue
            dist_end[prev] = dist_end[current] + 1
            queue.append(prev)

    has_ending = bool(endings)
    max_depth = max(depth.values()) if depth else 0
    ordered = sorted(nodes, key=lambda item: (item["sort_order"], item["id"]))
    span = max(len(ordered) - 1, 1)
    rank = {item["id"]: index for index, item in enumerate(ordered)}
    percents = {}
    for item in nodes:
        node_id = item["id"]
        if item["is_ending"]:
            percents[node_id] = 100
            continue
        if node_id not in depth:
            percent = round(rank[node_id] / span * 100)
            percents[node_id] = min(99, percent)
            continue
        node_depth = depth[node_id]
        remaining = dist_end.get(node_id)
        if has_ending and remaining:
            total = node_depth + remaining
            percent = round(node_depth / total * 100) if total else 0
            percents[node_id] = min(99, percent)
            continue
        if not has_ending and (max_depth == 0 or node_depth >= max_depth):
            percents[node_id] = 100
            continue
        if max_depth == 0:
            percents[node_id] = 0
            continue
        percents[node_id] = min(99, round(node_depth / max_depth * 100))
    return percents


def _local_day(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        return timezone.localtime(value).date()
    return value.date()


def _parse_day(raw):
    text = (raw or "").strip()
    if text:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return timezone.localdate()


def _chosen_day(raw, today):
    """空值返回空。非法或未来的日期收回到今天。"""
    if not (raw or "").strip():
        return None
    day = _parse_day(raw)
    return today if day > today else day


def _chosen_range(raw_from, raw_to, today, default_days):
    """收成不超过上限的闭区间。缺结束日用今天，缺开始日往前补默认天数。"""
    end = _chosen_day(raw_to, today) or today
    start = _chosen_day(raw_from, today)
    if start is None:
        start = end - timedelta(days=default_days - 1)
    if start > end:
        start = end
    if (end - start).days > RETENTION_SPAN - 1:
        start = end - timedelta(days=RETENTION_SPAN - 1)
    return start, end


def _aware_day_start(day):
    start = datetime.combine(day, datetime.min.time())
    if timezone.is_naive(start):
        return timezone.make_aware(start, timezone.get_current_timezone())
    return start


def _percent_rate(count, total):
    if not total:
        return None
    return int(round(count * 100 / total))


def _scoped_games(request):
    games = visible_games(request).order_by("sort_order", "-id")
    raw = request.query_params.get("game")
    if raw:
        try:
            games = games.filter(id=int(raw))
        except (TypeError, ValueError):
            games = games.none()
    return list(games)


def _player_progress(game_ids):
    """(game_id, player_id) -> 当前自动存档对应的进度百分比。没有存档的人不在结果里。"""
    if not game_ids:
        return {}
    nodes_by_game = defaultdict(list)
    edges_by_game = defaultdict(list)
    for item in OtomeNode.objects.filter(game_id__in=game_ids, is_deleted=False).values(
        "id", "game_id", "is_start", "is_ending", "next_node_id", "sort_order",
    ):
        nodes_by_game[item["game_id"]].append(item)
    for owner_id, source, target in OtomeChoice.objects.filter(
        node__game_id__in=game_ids,
        node__is_deleted=False,
        next_node__is_deleted=False,
    ).values_list("node__game_id", "node_id", "next_node_id"):
        edges_by_game[owner_id].append((source, target))
    percents = {
        game_id: story_progress_percents(nodes_by_game.get(game_id, []), edges_by_game.get(game_id, []))
        for game_id in game_ids
    }
    progress_of = {}
    for owner_id, player_id, node_id in OtomeSave.objects.filter(
        game_id__in=game_ids, is_auto=True,
    ).values_list("game_id", "player_id", "node_id"):
        progress_of[(owner_id, player_id)] = percents.get(owner_id, {}).get(node_id, 0)
    return progress_of


def _players_of_lang(raw):
    text = str(raw or "").strip()
    if not text:
        return None
    code = canonical(text)
    if not code:
        return set()
    return set(OtomePlayer.objects.filter(lang=code).values_list("id", flat=True))


def _ad_people(game_ids, start, end, lang=""):
    """一段日期里落地页广告的去重人数。对上玩家的按玩家计，否则按设备号或 IP。"""
    if not game_ids:
        return 0
    seen = set()
    rows = OtomeAdClick.objects.filter(
        channel__game_id__in=game_ids,
        created_at__gte=_aware_day_start(start),
        created_at__lt=_aware_day_start(end + timedelta(days=1)),
    )
    code = canonical(lang)
    if str(lang or "").strip():
        if not code:
            return 0
        rows = rows.filter(channel__lang=code)
    rows = rows.values_list(
        "player_id", "device_id", "ip", "click_id",
    )
    for player_id, device_id, ip, click_id in rows:
        if player_id:
            seen.add(("p", player_id))
        elif device_id:
            seen.add(("d", device_id))
        elif ip:
            seen.add(("i", ip))
        else:
            seen.add(("c", click_id))
    return len(seen)


class StaffLoginView(APIView):
    """一套后台登录。超管可以看全部游戏，其他账号看自己创建的和被分配的游戏。"""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = str(request.data.get("username") or "").strip()
        password = str(request.data.get("password") or "")
        if not username or not password:
            return ApiResponse(message="请填写用户名和密码", code=400)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return ApiResponse(message="用户名或密码错误", code=400)
        if user.role not in STAFF_ROLES:
            return ApiResponse(message="这个账号不能进入后台", code=403)
        if user.status != 1:
            return ApiResponse(message="这个账号已停用", code=403)
        if not verify_password(password, user.password):
            return ApiResponse(message="用户名或密码错误", code=400)
        logger.info("乙游后台登录 user=%s", user.username)
        return ApiResponse(
            data={"token": issue_staff_token(user), "username": user.username, "role": user.role},
            message="登录成功",
        )


def _data_queryset(request):
    queryset = OtomeDataRecord.objects.select_related("player", "game").order_by("-id")
    if not sees_all_games(request):
        queryset = queryset.filter(game__in=visible_games(request))
    game_id = request.query_params.get("game")
    kind = request.query_params.get("kind") or ""
    keyword = (request.query_params.get("q") or "").strip()
    today = timezone.localdate()
    start = _chosen_day(request.query_params.get("date_from"), today)
    end = _chosen_day(request.query_params.get("date_to"), today)
    if start and end and start > end:
        start, end = end, start
    if game_id:
        queryset = queryset.filter(game_id=game_id)
    if start:
        queryset = queryset.filter(created_at__gte=_aware_day_start(start))
    if end:
        queryset = queryset.filter(created_at__lt=_aware_day_start(end + timedelta(days=1)))
    if kind in KIND_LABEL:
        queryset = queryset.filter(kind=kind)
    queryset = filter_lang(queryset, request.query_params.get("lang"))
    if keyword:
        queryset = queryset.filter(
            Q(player__uid__icontains=keyword)
            | Q(title__icontains=keyword)
            | Q(detail__icontains=keyword)
            | Q(player__email__icontains=keyword)
        )
    return queryset


def _record_time(value):
    if not value:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%Y-%m-%d %H:%M:%S")


class AdminDataView(APIView):
    permission_classes = [IsOtomeAdmin]

    def get(self, request):
        queryset = _data_queryset(request)
        page_size = 30
        try:
            page_size = min(int(request.query_params.get("pageSize") or 30), 100)
        except ValueError:
            page_size = 30
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(request.query_params.get("currentPage") or 1)
        rows = []
        for item in page.object_list:
            rows.append({
                "id": item.id,
                "created_at": _record_time(item.created_at),
                "game_id": item.game_id,
                "game_title": item.game.title,
                "lang": item.lang,
                "lang_label": lang_name(item.lang),
                "kind": item.kind,
                "kind_label": tr(KIND_LABEL.get(item.kind, item.kind)),
                "uid": item.player.uid,
                "title": item.title,
                "detail": item.detail,
            })
        return ApiResponse(data=rows, pagination={
            "page": page.number,
            "page_size": page_size,
            "total": paginator.count,
            "total_pages": paginator.num_pages,
        })


class AdminDataExportView(APIView):
    """按和列表相同的筛选条件，导出全部明细。"""

    permission_classes = [IsOtomeAdmin]

    def get(self, request):
        filename = f"数据列表-{timezone.localdate().isoformat()}.csv"
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f"attachment; filename=\"data.csv\"; filename*=UTF-8''{quote(filename)}"
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([tr("时间"), tr("游戏"), tr("语言"), tr("类型"), "UID", tr("内容"), tr("说明")])
        for item in _data_queryset(request).iterator():
            writer.writerow([
                _record_time(item.created_at),
                item.game.title,
                lang_name(item.lang),
                tr(KIND_LABEL.get(item.kind, item.kind)),
                item.player.uid,
                item.title,
                item.detail,
            ])
        return response


class AdminInsightsView(APIView):
    """概览、进度漏斗和留存宽表。活跃按当天有登录、存档、解锁或进度记录计算。

    图表用 date_from 到 date_to，概览用 overview_from 到 overview_to，
    留存用 retention_from 到 retention_to。漏斗始终带上当前可见的全部游戏。
    """

    permission_classes = [IsOtomeAdmin]

    def get(self, request):
        scoped_rows = _scoped_games(request)
        funnel_rows = list(visible_games(request).order_by("sort_order", "-id"))
        game_ids = [item.id for item in scoped_rows]
        funnel_ids = [item.id for item in funnel_rows]
        scoped_ids = set(game_ids)
        today = timezone.localdate()
        chart_from, chart_to = _chosen_range(
            request.query_params.get("date_from"),
            request.query_params.get("date_to"),
            today,
            RETENTION_DAYS,
        )
        overview_from, overview_to = _chosen_range(
            request.query_params.get("overview_from"),
            request.query_params.get("overview_to"),
            today,
            RETENTION_DAYS,
        )
        retention_from, retention_to = _chosen_range(
            request.query_params.get("retention_from"),
            request.query_params.get("retention_to"),
            today,
            RETENTION_DAYS,
        )
        activity_start = min(retention_from, overview_from)
        activity_end = min(today, max(retention_to + timedelta(days=30), overview_to))
        channel_code = (request.query_params.get("channel") or "").strip()[:16]
        chart_players = _players_of_lang(request.query_params.get("chart_lang"))
        retention_players = _players_of_lang(request.query_params.get("retention_lang"))
        overview_players = _players_of_lang(request.query_params.get("overview_lang"))
        channel_players = None
        if channel_code:
            channel_players = set(
                OtomePlayer.objects.filter(
                    channel__channel_id=channel_code,
                    channel__is_deleted=False,
                    channel__game__in=visible_games(request),
                ).values_list("id", flat=True)
            )
        progress_of = _player_progress(funnel_ids)

        joined = {}
        joined_by_game = defaultdict(list)
        if funnel_ids:
            for owner_id, player_id, created_at in OtomePlayerGame.objects.filter(game_id__in=funnel_ids).values_list(
                "game_id", "player_id", "created_at",
            ):
                day = _local_day(created_at)
                joined_by_game[owner_id].append((player_id, day))
                if owner_id not in scoped_ids:
                    continue
                previous = joined.get(player_id)
                if previous is None or day < previous:
                    joined[player_id] = day

        activity = set()
        if game_ids:
            start_at = _aware_day_start(activity_start)
            end_at = _aware_day_start(activity_end + timedelta(days=1))
            for player_id, created_at in OtomeDataRecord.objects.filter(
                game_id__in=game_ids,
                created_at__gte=start_at,
                created_at__lt=end_at,
            ).values_list("player_id", "created_at"):
                activity.add((player_id, _local_day(created_at)))

        funnels = []
        for game in funnel_rows:
            members = [
                player_id for player_id, day in joined_by_game.get(game.id, [])
                if chart_from <= day <= chart_to and (channel_players is None or player_id in channel_players) and (chart_players is None or player_id in chart_players)
            ]
            total = len(members)
            steps = []
            for threshold, label in FUNNEL_STEPS:
                if threshold == 0:
                    count = total
                else:
                    count = sum(1 for player_id in members if progress_of.get((game.id, player_id), 0) >= threshold)
                steps.append({
                    "label": tr(label),
                    "threshold": threshold,
                    "count": count,
                    "rate": _percent_rate(count, total) or 0,
                })
            funnels.append({"id": game.id, "title": game.title, "players": total, "steps": steps})

        columns = [{"key": key, "label": tr(label)} for _offset, label, key in RETENTION_OFFSETS]
        rows = []
        span = (retention_to - retention_from).days
        for offset in range(span + 1):
            day = retention_to - timedelta(days=offset)
            members = [
                player_id for player_id, joined_on in joined.items()
                if joined_on == day and (retention_players is None or player_id in retention_players)
            ]
            cells = []
            for day_offset, _label, key in RETENTION_OFFSETS:
                target = day + timedelta(days=day_offset)
                ready = target <= today
                if not ready or not members:
                    cells.append({"key": key, "count": 0 if ready else None, "rate": None, "ready": ready})
                    continue
                kept = sum(1 for player_id in members if (player_id, target) in activity)
                cells.append({
                    "key": key,
                    "count": kept,
                    "rate": _percent_rate(kept, len(members)),
                    "ready": True,
                })
            rows.append({
                "date": day.isoformat(),
                "new_users": len(members),
                "cells": cells,
            })

        channel_counts = defaultdict(int)
        player_ids = [
            player_id for player_id, joined_on in joined.items()
            if overview_from <= joined_on <= overview_to and (overview_players is None or player_id in overview_players)
        ]
        if player_ids:
            for name, deleted in OtomePlayer.objects.filter(id__in=player_ids).values_list(
                "channel__name", "channel__is_deleted",
            ):
                if name and not deleted:
                    channel_counts[name] += 1
                else:
                    channel_counts[tr("自然量")] += 1
        channel_total = sum(channel_counts.values())
        channels = [
            {"name": name, "count": count, "share": _percent_rate(count, channel_total) or 0}
            for name, count in sorted(channel_counts.items(), key=lambda item: (-item[1], item[0]))
        ]

        def cohort_return(days_ago):
            cohort_from = overview_from - timedelta(days=days_ago)
            cohort_to = overview_to - timedelta(days=days_ago)
            members = [
                player_id for player_id, joined_on in joined.items()
                if cohort_from <= joined_on <= cohort_to and (overview_players is None or player_id in overview_players)
            ]
            retained = sum(
                1 for player_id, joined_on in joined.items()
                if cohort_from <= joined_on <= cohort_to
                and (overview_players is None or player_id in overview_players)
                and (player_id, joined_on + timedelta(days=days_ago)) in activity
            )
            return {
                "date": cohort_from.isoformat(),
                "end": cohort_to.isoformat(),
                "cohort": len(members),
                "retained": retained,
                "rate": _percent_rate(retained, len(members)),
            }

        source_rows = OtomeAdChannel.objects.filter(
            is_deleted=False, game__in=visible_games(request),
        ).select_related("game").order_by("game_id", "-id")
        source_rows = filter_lang(source_rows, request.query_params.get("chart_lang"))
        source_channels = [
            {
                "channel_id": item.channel_id,
                "name": item.name,
                "game_id": item.game_id,
                "game_title": item.game.title,
                "lang": item.lang,
            }
            for item in source_rows
        ]

        return ApiResponse(data={
            "date_from": chart_from.isoformat(),
            "date_to": chart_to.isoformat(),
            "channel": channel_code,
            "source_channels": source_channels,
            "today": today.isoformat(),
            "overview_from": overview_from.isoformat(),
            "overview_to": overview_to.isoformat(),
            "retention_from": retention_from.isoformat(),
            "retention_to": retention_to.isoformat(),
            "overview": {
                "new_users": len(player_ids),
                "dau": len({
                    player_id for player_id, day in activity
                    if overview_from <= day <= overview_to
                }),
                "retention_3": cohort_return(3),
                "retention_7": cohort_return(7),
                "ad_people": _ad_people(game_ids, overview_from, overview_to, request.query_params.get("overview_lang") or ""),
                "channels": channels,
            },
            "funnels": funnels,
            "retention": {"columns": columns, "rows": rows},
        })


def _can_manage_staff(request):
    staff = current_staff(request)
    if staff is not None and staff.role in ("admin", "super_admin"):
        return True
    return sees_all_games(request)


def _manages_admins(request):
    """超级管理员才能创建和修改管理员。"""
    return sees_all_games(request)


def _staff_scope_games(raw_ids, request):
    game_ids = []
    for raw in raw_ids or []:
        try:
            game_ids.append(int(raw))
        except (TypeError, ValueError):
            return None, "权限范围里有无法识别的游戏"
    unique = list(dict.fromkeys(game_ids))
    games = list(OtomeGame.objects.filter(id__in=unique, is_deleted=False))
    if len(games) != len(unique):
        return None, "权限范围里有不存在的游戏"
    if not sees_all_games(request):
        allowed = set(visible_games(request).values_list("id", flat=True))
        if any(item.id not in allowed for item in games):
            return None, "不能分配无权管理的游戏"
    return games, ""


def _replace_staff_scope(user, games):
    if user.role == "super_admin":
        OtomeStaffGame.objects.filter(user=user).delete()
        return
    OtomeStaffGame.objects.filter(user=user).exclude(game__in=games).delete()
    for item in games:
        OtomeStaffGame.objects.get_or_create(user=user, game=item)


class AdminUserView(APIView):
    permission_classes = [IsOtomeAdmin]

    def get(self, request):
        game_id = request.query_params.get("game") or ""
        side = request.query_params.get("side") or ""
        keyword = (request.query_params.get("q") or "").strip()
        lang = canonical(request.query_params.get("lang"))
        if str(request.query_params.get("lang") or "").strip() and not lang:
            lang = "__none__"
        allowed = visible_games(request).order_by("sort_order", "-id")
        games = [{"id": item.id, "title": item.title} for item in allowed]
        allowed_ids = {item["id"] for item in games}
        if game_id and not sees_all_games(request):
            try:
                picked = int(game_id)
            except (TypeError, ValueError):
                picked = None
            if picked not in allowed_ids:
                return ApiResponse(data={"frontend": [], "backend": [], "games": games})
        frontend = []
        backend = []
        if side != "backend":
            players = OtomePlayer.objects.select_related("channel").prefetch_related("game_links__game").order_by("-id")
            if game_id:
                players = players.filter(game_links__game_id=game_id)
            if lang == "__none__":
                players = players.none()
            elif lang:
                players = players.filter(lang=lang)
            if keyword:
                players = players.filter(
                    Q(uid__icontains=keyword)
                    | Q(nickname__icontains=keyword)
                    | Q(email__icontains=keyword)
                    | Q(device_id__icontains=keyword)
                )
            player_rows = list(players.distinct()[:200])
            tags_of = {}
            game_ids = set()
            for player in player_rows:
                tags = [
                    {"id": link.game_id, "title": link.game.title}
                    for link in player.game_links.all()
                    if not link.game.is_deleted and (sees_all_games(request) or link.game_id in allowed_ids)
                ]
                tags_of[player.id] = tags
                game_ids.update(item["id"] for item in tags)
            progress_of = _player_progress(list(game_ids))
            place_of = {}
            player_ids = [item.id for item in player_rows]
            if player_ids and game_ids:
                for owner_id, player_id, node_key in OtomeSave.objects.filter(
                    player_id__in=player_ids,
                    game_id__in=game_ids,
                    is_auto=True,
                ).values_list("game_id", "player_id", "node_key"):
                    place_of[(owner_id, player_id)] = node_key
            for player in player_rows:
                tags = tags_of[player.id]
                progress = []
                for tag in tags:
                    key = (tag["id"], player.id)
                    progress.append({
                        "id": tag["id"],
                        "title": tag["title"],
                        "percent": progress_of[key] if key in progress_of else None,
                        "node_key": place_of.get(key, ""),
                    })
                frontend.append({
                    "id": player.id,
                    "side": "frontend",
                    "uid": player.uid,
                    "name": player.nickname or player.uid,
                    "email": player.email,
                    "login_label": "Google" if player.login_type == OtomePlayer.LOGIN_GOOGLE else tr("设备快速登录"),
                    "lang": player.lang,
                    "lang_label": lang_name(player.lang),
                    "channel_id": player.channel.channel_id if player.channel_id and not player.channel.is_deleted else "",
                    "channel_name": player.channel.name if player.channel_id and not player.channel.is_deleted else "",
                    "created_at": _record_time(player.created_at),
                    "game_ids": [item["id"] for item in tags],
                    "tags": tags,
                    "progress": progress,
                })
        if side != "frontend":
            users = User.objects.filter(role__in=STAFF_ROLES).prefetch_related("game_tags__game").order_by("-id")
            if game_id:
                users = users.filter(game_tags__game_id=game_id)
            if lang == "__none__":
                users = users.none()
            elif lang:
                users = users.filter(lang=lang)
            if keyword:
                users = users.filter(Q(username__icontains=keyword) | Q(email__icontains=keyword))
            for user in users.distinct()[:200]:
                tags = [
                    {"id": link.game_id, "title": link.game.title}
                    for link in user.game_tags.all()
                    if not link.game.is_deleted
                ]
                backend.append({
                    "id": user.id,
                    "side": "backend",
                    "name": user.username,
                    "email": user.email,
                    "role": user.role,
                    "lang": user.lang,
                    "lang_label": lang_name(user.lang),
                    "game_ids": [item["id"] for item in tags],
                    "tags": tags,
                })
        staff = current_staff(request)
        return ApiResponse(data={
            "frontend": frontend,
            "backend": backend,
            "games": games,
            "can_manage": _can_manage_staff(request),
            "viewer_role": staff.role if staff else ("super_admin" if sees_all_games(request) else ""),
            "viewer_id": staff.id if staff else None,
        })

    def post(self, request):
        """管理员创建运营，超级管理员还可以创建管理员。"""
        if not _can_manage_staff(request):
            return ApiResponse(message="只有管理员或超级管理员可以创建后台用户", code=400)
        username = str(request.data.get("username") or "").strip()
        email = str(request.data.get("email") or "").strip()
        password = str(request.data.get("password") or "")
        role = str(request.data.get("role") or "operator")
        if role not in STAFF_ROLES:
            return ApiResponse(message="请选择角色", code=400)
        if role in ("admin", "super_admin") and not _manages_admins(request):
            return ApiResponse(message="只有超级管理员可以设置管理员", code=400)
        if not 2 <= len(username) <= 20:
            return ApiResponse(message="用户名需要 2 到 20 个字符", code=400)
        if "@" not in email or len(email) > 254:
            return ApiResponse(message="请填写有效邮箱", code=400)
        if len(password) < 6:
            return ApiResponse(message="密码至少 6 位", code=400)
        lang = clean_lang(request.data.get("lang"))
        if lang is None:
            return ApiResponse(message="请选择语言", code=400)
        if User.objects.filter(username=username).exists():
            return ApiResponse(message="用户名已存在", code=400)
        if User.objects.filter(email=email).exists():
            return ApiResponse(message="邮箱已存在", code=400)
        games, error = _staff_scope_games(request.data.get("game_ids"), request)
        if error:
            return ApiResponse(message=error, code=400)
        try:
            user = User(username=username, email=email, password=password, role=role, lang=lang, status=1)
            user.save()
        except IntegrityError:
            return ApiResponse(message="用户名或邮箱已存在", code=400)
        _replace_staff_scope(user, games)
        logger.info("超管创建后台用户 user=%s role=%s", user.username, user.role)
        return ApiResponse(message="用户已创建")


class AdminUserTagView(APIView):
    permission_classes = [IsOtomeAdmin]

    def post(self, request):
        side = request.data.get("side")
        owner_id = request.data.get("owner_id")
        raw_ids = request.data.get("game_ids") or []
        if side == "backend":
            if not _can_manage_staff(request):
                return ApiResponse(message="只有管理员或超级管理员可以设置权限范围", code=400)
        else:
            game_ids = []
            for raw in raw_ids:
                try:
                    game_ids.append(int(raw))
                except (TypeError, ValueError):
                    continue
            games = list(visible_games(request).filter(id__in=game_ids))
            if len(games) != len(set(game_ids)):
                return ApiResponse(message="不能操作这部游戏", code=403)
        try:
            if side == "frontend":
                player = OtomePlayer.objects.get(id=owner_id)
                tag_scope = OtomePlayerGame.objects.filter(player=player)
                if not sees_all_games(request):
                    tag_scope = tag_scope.filter(game__in=visible_games(request))
                tag_scope.exclude(game__in=games).delete()
                for item in games:
                    OtomePlayerGame.objects.get_or_create(player=player, game=item)
                logger.info("接口更新前端用户标签 uid=%s", player.uid)
                return ApiResponse(message="标签已保存")
            if side == "backend":
                user = User.objects.get(id=owner_id)
                if user.role not in STAFF_ROLES:
                    return ApiResponse(message="这个账号不是后台用户", code=400)
                role = str(request.data.get("role") or user.role)
                if role not in STAFF_ROLES:
                    return ApiResponse(message="请选择角色", code=400)
                if (user.role in ("admin", "super_admin") or role in ("admin", "super_admin")) and not _manages_admins(request):
                    return ApiResponse(message="只有超级管理员可以管理管理员", code=400)
                actor = current_staff(request)
                if actor is not None and actor.id == user.id and role != "super_admin":
                    return ApiResponse(message="不能取消自己的超级管理员权限", code=400)
                games, error = _staff_scope_games(raw_ids, request)
                if error:
                    return ApiResponse(message=error, code=400)
                user.role = role
                update_fields = ["role", "updated_at"]
                if "lang" in request.data:
                    lang = clean_lang(request.data.get("lang"))
                    if lang is None:
                        return ApiResponse(message="请选择语言", code=400)
                    user.lang = lang
                    update_fields.append("lang")
                user.save(update_fields=update_fields)
                _replace_staff_scope(user, games)
                logger.info("超管更新后台用户权限 user=%s role=%s", user.username, user.role)
                return ApiResponse(message="权限已保存")
        except (OtomePlayer.DoesNotExist, User.DoesNotExist):
            return ApiResponse(message="用户不存在", code=404)
        except Exception:
            logger.error("保存用户游戏标签失败", exc_info=True)
            return ApiResponse(message="保存标签失败", code=500)
        return ApiResponse(message="无法识别的用户类型", code=400)
