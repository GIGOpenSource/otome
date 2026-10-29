from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("models", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="otomeasset",
            index=models.Index(fields=["game", "is_deleted", "-id"], name="otome_asset_game_alive"),
        ),
        migrations.AddIndex(
            model_name="otomegalleryitem",
            index=models.Index(fields=["game", "is_deleted", "sort_order", "id"], name="otome_gallery_game_alive"),
        ),
    ]
