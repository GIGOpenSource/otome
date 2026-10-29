from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("models", "0003_character_image_screen_size"),
    ]

    operations = [
        migrations.AddField(
            model_name="otomeasset",
            name="duration",
            field=models.FloatField(
                blank=True,
                help_text="音频时长，单位秒。图片和视频为空",
                null=True,
                verbose_name="时长",
            ),
        ),
        migrations.AddField(
            model_name="otomeasset",
            name="file_size",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="文件字节数",
                null=True,
                verbose_name="大小",
            ),
        ),
    ]
