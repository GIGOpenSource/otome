from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from Apps.views.Otome.game_sheet import SheetError, export_game
from models.models import OtomeGame


class Command(BaseCommand):
    help = "把一部游戏导出成可再导入的配置表。"

    def add_arguments(self, parser):
        parser.add_argument("--game", default="", help="游戏 ID 或故事编码。只有一部游戏时可以不填。")
        parser.add_argument("--output", default="", help="xlsx 路径。默认写到项目目录。")

    def handle(self, *args, **options):
        game = _pick_game(options["game"])
        backend_root = Path(settings.BASE_DIR)
        if not (backend_root / "manage.py").exists():
            backend_root = backend_root.parent
        output = options["output"] or str(backend_root.parent / f"游戏配置-{game.title}.xlsx")
        try:
            path = export_game(game, output)
        except SheetError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"已导出《{game.title}》：{path}"))


def _pick_game(raw):
    text = (raw or "").strip()
    queryset = OtomeGame.objects.filter(is_deleted=False)
    if text.isdigit():
        game = queryset.filter(id=int(text)).first()
    elif text:
        game = queryset.filter(code=text).first() or queryset.filter(title=text).first()
    else:
        games = list(queryset.order_by("sort_order", "id")[:2])
        if len(games) != 1:
            raise CommandError("有多部游戏时请用 --game 指定 ID 或故事编码")
        game = games[0]
    if game is None:
        raise CommandError("找不到这部游戏")
    return game
