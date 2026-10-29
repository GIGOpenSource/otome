from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("models", "0004_asset_audio_duration_size"),
    ]

    operations = [
        migrations.AddField(
            model_name="otomegame",
            name="splash_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="进入游戏时先显示的竖屏开屏图。可存上传后的网址，也可由素材编号换算",
                max_length=500,
                verbose_name="开屏竖屏",
            ),
        ),
        migrations.AddField(
            model_name="otomegame",
            name="splash_land_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="进入游戏时先显示的横屏开屏图。可存上传后的网址，也可由素材编号换算",
                max_length=500,
                verbose_name="开屏横屏",
            ),
        ),
    ]
