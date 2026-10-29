from django.core.management.base import BaseCommand, CommandError

from Apps.views.Otome.game_sheet import SheetError, import_game


class Command(BaseCommand):
    help = "从配置表导入或更新一部游戏。故事编码相同则更新，不会另建一部。"

    def add_arguments(self, parser):
        parser.add_argument("path", help="xlsx 路径")
        parser.add_argument("--dry-run", action="store_true", help="只检查表格，不写入")

    def handle(self, *args, **options):
        try:
            result = import_game(options["path"], dry_run=options["dry_run"])
        except SheetError as exc:
            raise CommandError(str(exc)) from exc
        title = result["title"]
        detail = f"素材 {result['assets']}，角色 {result['characters']}，剧情 {result['nodes']}，选项 {result['choices']}，解锁 {result['gallery']}"
        if result["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"《{title}》可以导入。{detail}"))
            return
        self.stdout.write(self.style.SUCCESS(f"《{title}》已导入，游戏 ID = {result['id']}。{detail}"))
