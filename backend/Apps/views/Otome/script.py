import logging

from Apps.views.Otome.content_i18n import field_text, narrator

logger = logging.getLogger(__name__)


def media_of(asset, request):
    """画面可以是图片或视频。没有素材时按图片处理，客户端会显示空背景。"""
    url = resolve_asset_url(asset, request)
    if not url:
        return "", "image"
    if getattr(asset, "asset_type", "") == "video":
        return url, "video"
    return url, "image"


def resolve_asset_url(asset, request):
    """外链优先。替换素材的地址后，所有引用它的剧情都会拿到新地址。"""
    if asset is None or getattr(asset, "is_deleted", False):
        return ""
    if asset.url:
        return asset.url
    if not asset.file:
        return ""
    try:
        relative = asset.file.url
    except Exception:
        logger.error("读取素材地址失败", exc_info=True)
        return ""
    if not relative:
        return ""
    if request is not None:
        return request.build_absolute_uri(relative)
    return relative


def _portrait_pair(node, char_map, request):
    """竖屏、横屏各取一张图或一段视频。节点没配时用角色立绘。"""
    character = char_map.get(node.character_id)
    portrait_url, portrait_kind = media_of(node.portrait, request)
    portrait_land_url, portrait_land_kind = media_of(node.portrait_land, request)
    if character is not None:
        if not portrait_url:
            portrait_url, portrait_kind = media_of(character.portrait, request)
        if not portrait_land_url:
            portrait_land_url, portrait_land_kind = media_of(character.portrait_land, request)
    return portrait_url, portrait_kind, portrait_land_url, portrait_land_kind


def _node_asset_urls(node, char_map, request):
    found = []
    for figure in node.figures.all():
        image = figure.image
        if image is None:
            continue
        for asset in (image.image, image.image_land):
            url = resolve_asset_url(asset, request)
            if url and url not in found:
                found.append(url)
    for asset in (node.background, node.background_land, node.bgm, node.voice, node.interact, node.insert_media):
        url = resolve_asset_url(asset, request)
        if url and url not in found:
            found.append(url)
    for choice in node.choices.all():
        url = resolve_asset_url(choice.interact, request)
        if url and url not in found:
            found.append(url)
    portrait_url, _portrait_kind, portrait_land_url, _portrait_land_kind = _portrait_pair(node, char_map, request)
    for url in (portrait_url, portrait_land_url):
        if url and url not in found:
            found.append(url)
    return found


def _segment_urls(origin_id, node_map, key_ids, char_map, request, cover_urls, start_id):
    """从关键节点走到下一个关键节点之前，收集这一段要预下载的资源。"""
    seen = set()
    ordered = []
    queue = [origin_id]
    while queue:
        current_id = queue.pop(0)
        if current_id in seen or current_id not in node_map:
            continue
        seen.add(current_id)
        if current_id in key_ids and current_id != origin_id:
            continue
        node = node_map[current_id]
        for url in _node_asset_urls(node, char_map, request):
            if url not in ordered:
                ordered.append(url)
        if node.next_node_id and node.next_node_id not in key_ids:
            queue.append(node.next_node_id)
        for choice in node.choices.all():
            if choice.next_node_id and choice.next_node_id not in key_ids:
                queue.append(choice.next_node_id)
    if origin_id == start_id:
        extra = [url for url in cover_urls if url and url not in ordered]
        ordered = extra + ordered
    return ordered


def _figure_payload(figure, request):
    image = figure.image if figure.image_id else None
    port = image.image if image is not None else None
    land = image.image_land if image is not None and image.image_land_id else None
    url, kind = media_of(port, request)
    land_url, land_kind = media_of(land, request)
    name = ""
    if figure.character_id and figure.character is not None:
        name = field_text(figure.character, "name")
    return {
        "position": figure.position,
        "url": url,
        "kind": kind,
        "land_url": land_url,
        "land_kind": land_kind,
        "name": name,
        "screen_size": image.screen_size if image is not None else 100,
    }


def _script_figures(node, request, portrait_url, portrait_kind, portrait_land_url, portrait_land_kind, speaker):
    rows = [_figure_payload(item, request) for item in node.figures.all()]
    rows = [item for item in rows if item["url"] or item["land_url"]]
    if rows:
        return rows
    if portrait_url or portrait_land_url:
        return [{
            "position": "e",
            "url": portrait_url,
            "kind": portrait_kind,
            "land_url": portrait_land_url,
            "land_kind": portrait_land_kind,
            "name": "" if speaker in ("旁白", narrator()) else speaker,
            "screen_size": 100,
        }]
    return []


def build_script(game, request):
    characters = list(
        game.characters.filter(is_deleted=False).select_related("portrait", "portrait_land").order_by("sort_order", "id")
    )
    nodes = list(
        game.nodes.filter(is_deleted=False)
        .select_related(
            "character", "character__portrait", "character__portrait_land",
            "background", "background_land", "portrait", "portrait_land", "bgm", "voice", "interact", "insert_media",
        )
        .prefetch_related("choices__interact", "figures__image__image", "figures__image__image_land", "figures__character")
        .order_by("sort_order", "id")
    )
    char_map = {item.id: item for item in characters}
    node_map = {item.id: item for item in nodes}
    start = next((item for item in nodes if item.is_start), None)
    if start is None and nodes:
        start = nodes[0]
    key_ids = {item.id for item in nodes if item.is_key or item.is_start}
    if start is not None:
        key_ids.add(start.id)
    start_id = start.id if start else None
    cover_url, cover_kind = media_of(game.cover, request)
    cover_land_url, cover_land_kind = media_of(game.cover_land, request)
    cover_urls = [cover_url, cover_land_url]
    segment_cache = {
        key_id: _segment_urls(key_id, node_map, key_ids, char_map, request, cover_urls, start_id)
        for key_id in key_ids
    }

    node_payload = []
    for node in nodes:
        character = char_map.get(node.character_id)
        raw_speaker = node.speaker_name or (character.name if character else "") or "旁白"
        if node.speaker_name:
            speaker = field_text(node, "speaker_name")
        elif character:
            speaker = field_text(character, "name")
        else:
            speaker = narrator()
        if character and character.name_color:
            color = character.name_color
        elif raw_speaker == "你":
            color = "#f3d2dc"
        else:
            color = "#e7c27a"
        portrait_url, portrait_kind, portrait_land_url, portrait_land_kind = _portrait_pair(node, char_map, request)
        background_url, background_kind = media_of(node.background, request)
        background_land_url, background_land_kind = media_of(node.background_land, request)
        insert_url, insert_kind = media_of(node.insert_media, request)
        insert_title = field_text(node, "insert_title") if node.insert_title else ""
        if not insert_title and insert_url and node.insert_media_id:
            insert_title = field_text(node.insert_media, "name")
        is_key = node.id in key_ids
        choices = []
        for choice in node.choices.all():
            if choice.next_node_id not in node_map:
                continue
            choices.append({
                "id": choice.id,
                "text": field_text(choice, "text"),
                "next_id": choice.next_node_id,
                "sort_order": choice.sort_order,
                "interact_url": resolve_asset_url(choice.interact, request),
            })
        node_payload.append({
            "id": node.id,
            "node_key": node.node_key,
            "sort_order": node.sort_order,
            "speaker_name": speaker,
            "name_color": color,
            "content": field_text(node, "content"),
            "background_url": background_url,
            "background_kind": background_kind,
            "background_land_url": background_land_url,
            "background_land_kind": background_land_kind,
            "portrait_url": portrait_url,
            "portrait_kind": portrait_kind,
            "portrait_land_url": portrait_land_url,
            "portrait_land_kind": portrait_land_kind,
            "cast_mode": node.cast_mode,
            "figures": _script_figures(node, request, portrait_url, portrait_kind, portrait_land_url, portrait_land_kind, speaker),
            "bgm_url": resolve_asset_url(node.bgm, request),
            "voice_url": resolve_asset_url(node.voice, request),
            "interact_url": resolve_asset_url(node.interact, request),
            "insert_url": insert_url,
            "insert_kind": insert_kind if insert_url else "",
            "insert_title": insert_title,
            "is_start": bool(node.is_start or node.id == start_id),
            "is_key": is_key,
            "is_ending": node.is_ending,
            "ending_title": field_text(node, "ending_title"),
            "next_id": node.next_node_id if node.next_node_id in node_map else None,
            "choices": choices,
            "preload_urls": segment_cache.get(node.id, []) if is_key else [],
        })

    return {
        "game": {
            "id": game.id,
            "code": game.code,
            "title": field_text(game, "title"),
            "subtitle": field_text(game, "subtitle"),
            "summary": field_text(game, "summary"),
            "cover_url": cover_url,
            "cover_kind": cover_kind,
            "cover_land_url": cover_land_url,
            "cover_land_kind": cover_land_kind,
            "splash_url": (game.splash_url or "").strip() or cover_url,
            "splash_land_url": (game.splash_land_url or "").strip() or cover_land_url,
            "status": game.status,
        },
        "characters": [
            {
                "id": item.id,
                "name": field_text(item, "name"),
                "title": field_text(item, "title"),
                "name_color": item.name_color,
                "intro": field_text(item, "intro"),
                "portrait_url": media_of(item.portrait, request)[0],
                "portrait_kind": media_of(item.portrait, request)[1],
                "portrait_land_url": media_of(item.portrait_land, request)[0],
                "portrait_land_kind": media_of(item.portrait_land, request)[1],
            }
            for item in characters
        ],
        "entry_node_id": start_id,
        "nodes": node_payload,
    }
