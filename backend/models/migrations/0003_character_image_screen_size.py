from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("models", "0002_asset_gallery_list_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="otomecharacterimage",
            name="screen_size",
            field=models.PositiveSmallIntegerField(
                default=100,
                help_text="立绘占画面的百分比，100 为铺满所在位置",
                verbose_name="占据画面的大小",
            ),
        ),
    ]
