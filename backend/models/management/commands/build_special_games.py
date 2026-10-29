"""把桌面专项里已经写完的男频、女频对白收成两部可导入的游戏。"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from openpyxl import Workbook

from Apps.views.Otome.game_sheet import (
    ASSET_HEADERS,
    CHARACTER_HEADERS,
    CHOICE_HEADERS,
    GALLERY_HEADERS,
    GAME_HEADERS,
    NODE_HEADERS,
    SHEET_ASSET,
    SHEET_CHARACTER,
    SHEET_CHOICE,
    SHEET_GALLERY,
    SHEET_GAME,
    SHEET_NODE,
    SheetError,
    _write_help,
    _write_sheet,
    import_game,
)

DEFAULT_ROOT = Path.home() / "Desktop" / "专项"

MALE = {
    "code": "first-night",
    "title": "第一夜",
    "subtitle": "第一场噩梦的七夜",
    "summary": "停电的出租屋里，影子比人先站起来。Sunny 不能说谎。他把真名交给谁，第七夜就由谁来点名。",
    "cover": "fn-cover",
    "cover_land": "fn-cover-land",
    "status": "已发布",
    "sort": 10,
    "plot": "男频-人气改编/剧本/剧情-Nephis线.csv",
    "choices": "男频-人气改编/剧本/选项-Nephis线.csv",
    "output": "游戏配置-第一夜.xlsx",
    "lead": "Nephis",
    "lead_portrait": "fn-ch-nephis",
    "player": "Sunny",
    "player_portrait": "fn-ch-sunny",
    "characters": [
        ("Sunny", "玩家", "fn-ch-sunny", "#f6efe4", "穷，清醒，不能说谎。真名留到第七夜才决定交不交出去。", 1),
        ("Spell", "噩梦的声音", "fn-ch-spell", "#c9b7e8", "点名的光。它不解释规则，也不进任何一条路线。", 2),
        ("Nephis", "把活人点清的人", "fn-ch-nephis", "#e7c27a", "清点活人，表情稳。真结局里她站到他旁边，而不是他前面。", 3),
        ("Cassie", "盲眼", "fn-ch-cassie", "#d9dde8", "眼睛不聚焦，听见没说出口的话。这条线还只有大纲。", 4),
        ("Effie", "冲在最前面的战士", "fn-ch-effie", "#d08a5a", "笑着，武器还提着。这条线还只有大纲。", 5),
        ("Kai", "把灯交给黑夜的人", "fn-ch-kai", "#8fb59a", "灯在他这边，弓放下。这条线还只有大纲。", 6),
        ("名册", "城门上的空格", "", "#8d93a8", "石壁上的空格。他的名字还没写上去。", 7),
    ],
    "catalog_images": {
        "fn-bg-room": ("背景", "竖屏", "出租屋、停电"),
        "fn-bg-gate": ("背景", "竖屏", "坍塌的城门、名册"),
        "fn-bg-ruin": ("背景", "竖屏", "噩梦废墟"),
        "fn-bg-hunt": ("背景", "竖屏", "第一场围猎"),
        "fn-bg-fire": ("背景", "竖屏", "火堆"),
        "fn-bg-dark": ("背景", "竖屏", "只有影子的走廊"),
        "fn-bg-altar": ("背景", "竖屏", "Spell 问真名的石台"),
        "fn-bg-exit": ("背景", "竖屏", "第七夜的出口"),
        "fn-cover": ("封面", "竖屏", "竖屏封面"),
        "fn-cover-land": ("封面", "横屏", "横屏封面"),
        "fn-ch-sunny": ("立绘", "竖屏", "穷，清醒，嘴闭着"),
        "fn-ch-sunny-shadow": ("立绘", "竖屏", "半张脸在影子里"),
        "fn-ch-sunny-name": ("立绘", "竖屏", "把真名说出来"),
        "fn-ch-sunny-near": ("立绘", "竖屏", "成人向，衬衫敞着"),
        "fn-ch-spell": ("立绘", "竖屏", "没有五官的光"),
        "fn-ch-nephis": ("立绘", "竖屏", "清点活人"),
        "fn-ch-nephis-side": ("立绘", "竖屏", "站在他旁边"),
        "fn-ch-nephis-near": ("立绘", "竖屏", "成人向，外套落下"),
        "fn-ch-cassie": ("立绘", "竖屏", "脸转向声音"),
        "fn-ch-cassie-hear": ("立绘", "竖屏", "听见了没说的那句"),
        "fn-ch-effie": ("立绘", "竖屏", "笑，武器还提着"),
        "fn-ch-effie-front": ("立绘", "竖屏", "把最前面的位置让开半步"),
        "fn-ch-kai": ("立绘", "竖屏", "灯在他这边"),
        "fn-ch-kai-dark": ("立绘", "竖屏", "灯还亮，人面向观众"),
    },
    "catalog_video": {
        "fn-cg-spell": "被点名",
        "fn-cg-hunt": "藏一手",
        "fn-cg-roster": "空格",
        "fn-cg-n-true": "名字在列",
        "fn-cg-n-near": "再靠近",
        "fn-cg-n-plain": "她替他签了",
        "fn-cg-c-true": "她听见了",
        "fn-cg-c-plain": "预言先到",
        "fn-cg-e-true": "半步",
        "fn-cg-e-plain": "冲在前面",
        "fn-cg-k-true": "灯灭了",
        "fn-cg-k-plain": "灯还亮着",
        "fn-cg-a-true": "影子回答",
        "fn-cg-a-plain": "空名离开",
    },
    "catalog_bgm": {
        "fn-bgm-room": "出租屋，很轻",
        "fn-bgm-ruin": "风穿过石头",
        "fn-bgm-hunt": "围猎",
        "fn-bgm-fire": "火堆",
        "fn-bgm-dark": "几乎只有呼吸",
        "fn-bgm-end-true": "真结局",
        "fn-bgm-end-plain": "普通结局",
    },
    "catalog_sfx": {
        "fn-sfx-choice": "普通选项",
        "fn-sfx-name": "把真名说出来",
    },
}

FEMALE = {
    "code": "shadow-first",
    "title": "影中第一",
    "subtitle": "选拔前的七天",
    "summary": "报名表压在药箱最下层。Skylar 跟在哥哥后面走进学院。半张纸最后会放上谁的桌子，决定她以什么名字站上试炼。",
    "cover": "cover-shadow",
    "cover_land": "cover-shadow-land",
    "status": "已发布",
    "sort": 20,
    "plot": "女频-人气改编/剧本/剧情-Cameron线.csv",
    "choices": "女频-人气改编/剧本/选项-Cameron线.csv",
    "output": "游戏配置-影中第一.xlsx",
    "lead": "Cameron",
    "lead_portrait": "ch-cameron-far",
    "player": "Skylar",
    "player_portrait": "ch-skylar-wary",
    "characters": [
        ("Skylar", "玩家", "ch-skylar-wary", "#f6efe4", "低头走路，领口能挡住淤青。实力藏着，还没被划掉。", 1),
        ("Mary", "保姆", "ch-mary", "#d7c4a3", "把报名表压在药箱最下层。安全的人，不进攻略。", 2),
        ("Sierra", "新来的训练伙伴", "ch-sierra", "#f0c27a", "第一个不肯配合她藏拙的人。", 3),
        ("Kaley", "霸凌者", "ch-kaley", "#c98598", "走廊里先伸过来的那只鞋。", 4),
        ("Mateo", "哥哥，未来 Beta", "ch-mateo", "#8d93a8", "走在前面，不回头。家族压力，不进攻略。", 5),
        ("Cameron", "未来 Alpha", "ch-cameron-far", "#e7c27a", "路口回头看了一眼，又转回去。真结局里他先说她的名字。", 6),
        ("Oliver", "未来 Gamma", "ch-oliver-guilt", "#8fb59a", "笑出声又停住。这条线还只有大纲。", 7),
        ("Sam", "未来 Delta", "ch-sam-focus", "#d08a5a", "盯着纪录，视线停在她收回去的拳头上。这条线还只有大纲。", 8),
        ("Dakota", "另一位未来 Alpha", "ch-dakota", "#c9b7e8", "灯留在训练场，人在树外。这条线还只有大纲。", 9),
        ("Alpha King", "王庭", "ch-king", "#d9dde8", "低台上的人。这条线还只有大纲。", 10),
        ("Reed", "守左门的人", "", "#8d93a8", "训练时不问姓，只看站位。流寇夜里他守左门。", 11),
        ("Hollis", "守右门的人", "", "#d7c4a3", "欠过低年级一次没有出声。流寇夜里他守右门。", 12),
    ],
    "catalog_images": {
        "bg-room": ("背景", "竖屏", "Mary 的房间、药箱"),
        "bg-path": ("背景", "竖屏", "上学的路"),
        "bg-hall": ("背景", "竖屏", "走廊"),
        "bg-class": ("背景", "竖屏", "课堂"),
        "bg-train": ("背景", "竖屏", "训练场、夜训"),
        "bg-board": ("背景", "竖屏", "纪录榜"),
        "bg-meeting": ("背景", "竖屏", "族群会议、正厅"),
        "bg-gate": ("背景", "竖屏", "侧门、流寇夜"),
        "bg-trial": ("背景", "竖屏", "试炼庭、点名"),
        "bg-archive": ("背景", "竖屏", "王庭档案房"),
        "cover-shadow": ("封面", "竖屏", "竖屏封面"),
        "cover-shadow-land": ("封面", "横屏", "横屏封面"),
        "ch-skylar-wary": ("立绘", "竖屏", "低头，领口挡住淤青"),
        "ch-skylar-hurt": ("立绘", "竖屏", "走廊里半跪"),
        "ch-skylar-stand": ("立绘", "竖屏", "试炼上站直"),
        "ch-skylar-soft": ("立绘", "竖屏", "看着药箱"),
        "ch-skylar-near": ("立绘", "竖屏", "成人向，窄领松开"),
        "ch-cameron-far": ("立绘", "竖屏", "回头看了一眼"),
        "ch-cameron-soft": ("立绘", "竖屏", "看见伤之后"),
        "ch-cameron-near": ("立绘", "竖屏", "成人向，先喊她的名字"),
        "ch-cameron-rank": ("立绘", "竖屏", "仍用头衔介绍她"),
        "ch-oliver-guilt": ("立绘", "竖屏", "笑停了一拍"),
        "ch-oliver-speak": ("立绘", "竖屏", "把那声笑讲完"),
        "ch-sam-focus": ("立绘", "竖屏", "盯着纪录"),
        "ch-sam-side": ("立绘", "竖屏", "站在她侧前方"),
        "ch-sierra": ("立绘", "竖屏", "夜训后留下"),
        "ch-kaley": ("立绘", "竖屏", "走廊"),
        "ch-mary": ("立绘", "竖屏", "房间"),
        "ch-mateo": ("立绘", "竖屏", "转过头去"),
        "ch-dakota": ("立绘", "竖屏", "灯影边上"),
        "ch-dakota-down": ("立绘", "竖屏", "从裁判席走下来"),
        "ch-king": ("立绘", "竖屏", "低台"),
        "ch-king-far": ("立绘", "竖屏", "保持距离"),
    },
    "catalog_video": {
        "cg-hall": "走廊",
        "cg-train": "夜训",
        "cg-board": "纪录",
        "cg-c-true": "他先说了你的名字",
        "cg-c-near": "侧门先不要关",
        "cg-c-plain": "位阶后面",
        "cg-o-true": "那声笑",
        "cg-o-plain": "侧门",
        "cg-s-true": "两个名字",
        "cg-s-plain": "空出的名额",
        "cg-d-true": "走下来",
        "cg-d-plain": "灯还亮着",
        "cg-k-true": "名字",
        "cg-k-plain": "任命",
    },
    "catalog_bgm": {
        "bgm-room": "室内，很轻",
        "bgm-hall": "走廊，压着",
        "bgm-train": "夜训",
        "bgm-meeting": "人很多",
        "bgm-gate": "侧门的风",
        "bgm-trial": "清晨",
        "bgm-end-true": "真结局",
        "bgm-end-plain": "普通结局",
    },
    "catalog_sfx": {
        "sfx-choice": "普通选项",
        "sfx-hurt": "把领口的伤给他看",
    },
}


class Command(BaseCommand):
    help = "把专项文件夹里的男频、女频对白做成两部游戏并导入。"

    def add_arguments(self, parser):
        parser.add_argument("--root", default=str(DEFAULT_ROOT), help="专项文件夹")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        root = Path(options["root"])
        if not root.is_dir():
            raise CommandError(f"找不到专项文件夹：{root}")
        project = Path(__file__).resolve().parents[4]
        for spec in (MALE, FEMALE):
            path = project / spec["output"]
            problems = build_workbook(root, spec, path)
            if problems:
                raise CommandError(spec["title"] + "\n" + "\n".join(problems))
            try:
                result = import_game(path, dry_run=options["dry_run"])
            except SheetError as exc:
                raise CommandError(str(exc)) from exc
            action = "可以导入" if result["dry_run"] else f"已导入，游戏 ID = {result['id']}"
            self.stdout.write(self.style.SUCCESS(
                f"《{result['title']}》{action}。素材 {result['assets']}，角色 {result['characters']}，"
                f"剧情 {result['nodes']}，选项 {result['choices']}，解锁 {result['gallery']}。表格：{path}"
            ))


def build_workbook(root, spec, path):
    nodes = _read_csv(root / spec["plot"])
    choices = _read_csv(root / spec["choices"])
    problems = _check_graph(nodes, choices)
    if problems:
        return problems
    choice_at = {row["所在剧情"] for row in choices}
    for row in nodes:
        if row["剧情编号"] in choice_at:
            row["下一句"] = ""
    assets = _assets(spec, nodes, choices)
    characters = _characters(spec)
    gallery = _gallery(spec, nodes)
    book = Workbook()
    _write_help(book.active)
    _write_sheet(book, SHEET_GAME, GAME_HEADERS, [[
        spec["code"], spec["title"], spec["subtitle"], spec["summary"],
        spec["cover"], spec["cover_land"], "", "", spec["status"], spec["sort"],
    ]])
    _write_sheet(book, SHEET_ASSET, ASSET_HEADERS, assets)
    _write_sheet(book, SHEET_CHARACTER, CHARACTER_HEADERS, characters)
    _write_sheet(book, SHEET_NODE, NODE_HEADERS, [_node_row(row) for row in nodes])
    _write_sheet(book, SHEET_CHOICE, CHOICE_HEADERS, [_choice_row(row) for row in choices])
    _write_sheet(book, SHEET_GALLERY, GALLERY_HEADERS, gallery)
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)
    return []


def _read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _node_row(row):
    return [row.get(header, "") for header in NODE_HEADERS]


def _choice_row(row):
    return [row.get(header, "") for header in CHOICE_HEADERS]


def _check_graph(nodes, choices):
    keys = [row["剧情编号"] for row in nodes]
    key_set = set(keys)
    problems = []
    if len(keys) != len(key_set):
        problems.append("剧情编号有重复")
    starts = [row["剧情编号"] for row in nodes if row.get("开场") == "是"]
    if starts != [keys[0]] and starts != ["P1-001"]:
        problems.append("开场不是唯一的 P1-001：" + "、".join(starts))
    choice_at = {}
    for row in choices:
        choice_at.setdefault(row["所在剧情"], []).append(row["跳转剧情"])
        if row["所在剧情"] not in key_set:
            problems.append(f"选项所在剧情不存在：{row['所在剧情']}")
        if row["跳转剧情"] not in key_set:
            problems.append(f"选项跳转不存在：{row['跳转剧情']}")
    for row in nodes:
        key = row["剧情编号"]
        nxt = (row.get("下一句") or "").strip()
        is_end = row.get("结局") == "是"
        has_choice = key in choice_at
        if nxt and nxt not in key_set:
            problems.append(f"{key} 的下一句不存在：{nxt}")
        if is_end and not (row.get("结局标题") or "").strip():
            problems.append(f"{key} 是结局，但没有结局标题")
        if is_end and (nxt or has_choice):
            problems.append(f"{key} 是结局，却还有下一句或选项")
        if not is_end and not nxt and not has_choice:
            problems.append(f"{key} 没有下一句，也不是结局")
    seen = set()
    stack = ["P1-001"]
    by_key = {row["剧情编号"]: row for row in nodes}
    while stack:
        key = stack.pop()
        if key in seen or key not in by_key:
            continue
        seen.add(key)
        row = by_key[key]
        nxt = (row.get("下一句") or "").strip()
        if key not in choice_at and nxt:
            stack.append(nxt)
        stack.extend(choice_at.get(key, []))
    missed = [key for key in keys if key not in seen]
    if missed:
        problems.append("从开场走不到：" + "、".join(missed[:12]))
    return problems


def _assets(spec, nodes, choices):
    rows = {}

    def add(name, kind, usage="", screen="", remark=""):
        name = (name or "").strip()
        if not name or name in rows:
            return
        rows[name] = [name, kind, usage, screen, "", "", remark]

    for name, (usage, screen, remark) in spec["catalog_images"].items():
        add(name, "图片", usage, screen, remark)
    for name, remark in spec["catalog_video"].items():
        add(name, "视频", remark=remark)
    for name, remark in spec["catalog_bgm"].items():
        add(name, "音频", remark=remark)
    for name, remark in spec["catalog_sfx"].items():
        add(name, "音频", remark=remark)
    for row in nodes:
        for field in ("竖屏背景", "横屏背景"):
            add(row.get(field), "图片", "背景", "竖屏", "剧情引用")
        for field in ("竖屏立绘", "横屏立绘"):
            add(row.get(field), "图片", "立绘", "竖屏", "剧情引用")
        for field in ("背景音乐", "语音", "交互音频"):
            add(row.get(field), "音频", remark="剧情引用")
        add(row.get("结束后插入"), "视频", remark=row.get("解锁标题") or "剧情插入")
    for row in choices:
        add(row.get("交互音频"), "音频", remark="选项")
    return list(rows.values())


def _characters(spec):
    rows = []
    for name, title, portrait, color, intro, sort in spec["characters"]:
        rows.append([name, title, portrait, portrait, color, intro, sort])
    return rows


def _gallery(spec, nodes):
    first_lead = ""
    for row in nodes:
        portraits = {(row.get("竖屏立绘") or "").strip(), (row.get("横屏立绘") or "").strip()}
        if spec["lead_portrait"] in portraits:
            first_lead = row["剧情编号"]
            break
    return [
        ["立绘", spec["player"], spec["player_portrait"], "", "是", 1, "手动"],
        ["立绘", spec["lead"], spec["lead_portrait"], first_lead, "否", 2, "手动"],
    ]
