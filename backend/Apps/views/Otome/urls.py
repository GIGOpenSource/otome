from django.urls import include, path
from rest_framework import routers

from Apps.views.Otome.admin_api import (
    AdminDataExportView,
    AdminDataView,
    AdminInsightsView,
    AdminUserTagView,
    AdminUserView,
    StaffLoginView,
)
from Apps.views.Otome.ads import (
    AdminAdChannelDetailView,
    AdminAdChannelView,
    AdminBuiltinAdDetailView,
    AdminBuiltinAdView,
    PlayAdsView,
    PlayAdTrackView,
)
from Apps.views.Otome.player import (
    DeviceLoginView,
    GalleryView,
    GoogleLoginView,
    PlayConfigView,
    PlayerMeView,
    ProgressView,
    SaveDetailView,
    SaveListView,
)
from Apps.views.Otome.view import (
    AssetUploadView,
    AssetViewSet,
    CharacterViewSet,
    ChoiceViewSet,
    GameBootView,
    GameResolveView,
    GameScriptView,
    GameViewSet,
    GalleryItemViewSet,
    NodeViewSet,
)

router = routers.DefaultRouter()
router.register(r"assets", AssetViewSet, basename="otome-asset")
router.register(r"games", GameViewSet, basename="otome-game")
router.register(r"characters", CharacterViewSet, basename="otome-character")
router.register(r"nodes", NodeViewSet, basename="otome-node")
router.register(r"choices", ChoiceViewSet, basename="otome-choice")
router.register(r"gallery", GalleryItemViewSet, basename="otome-gallery-admin")

urlpatterns = [
    path("admin/login/", StaffLoginView.as_view(), name="otome-admin-login"),
    path("admin/data/", AdminDataView.as_view(), name="otome-admin-data"),
    path("admin/data/export/", AdminDataExportView.as_view(), name="otome-admin-data-export"),
    path("admin/data/insights/", AdminInsightsView.as_view(), name="otome-admin-insights"),
    path("admin/users/", AdminUserView.as_view(), name="otome-admin-users"),
    path("admin/users/tags/", AdminUserTagView.as_view(), name="otome-admin-user-tags"),
    path("admin/ads/channels/", AdminAdChannelView.as_view(), name="otome-admin-ad-channels"),
    path("admin/ads/channels/<int:channel_pk>/", AdminAdChannelDetailView.as_view(), name="otome-admin-ad-channel"),
    path("admin/ads/builtins/", AdminBuiltinAdView.as_view(), name="otome-admin-builtin-ads"),
    path("admin/ads/builtins/<int:ad_pk>/", AdminBuiltinAdDetailView.as_view(), name="otome-admin-builtin-ad"),
    path("play/games/<int:game_id>/ads/", PlayAdsView.as_view(), name="otome-play-ads"),
    path("play/games/<int:game_id>/ads/<int:ad_id>/track/", PlayAdTrackView.as_view(), name="otome-play-ad-track"),
    path("play/config/", PlayConfigView.as_view(), name="otome-play-config"),
    path("play/auth/device/", DeviceLoginView.as_view(), name="otome-auth-device"),
    path("play/auth/google/", GoogleLoginView.as_view(), name="otome-auth-google"),
    path("play/me/", PlayerMeView.as_view(), name="otome-play-me"),
    path("play/games/resolve/", GameResolveView.as_view(), name="otome-resolve"),
    path("play/games/boot/", GameBootView.as_view(), name="otome-boot"),
    path("play/games/<int:game_id>/script/", GameScriptView.as_view(), name="otome-script"),
    path("play/games/<int:game_id>/saves/", SaveListView.as_view(), name="otome-saves"),
    path("play/games/<int:game_id>/saves/<int:save_id>/", SaveDetailView.as_view(), name="otome-save"),
    path("play/games/<int:game_id>/gallery/", GalleryView.as_view(), name="otome-gallery"),
    path("play/games/<int:game_id>/progress/", ProgressView.as_view(), name="otome-progress"),
    path("assets/upload/", AssetUploadView.as_view(), name="otome-asset-upload"),
    path("", include(router.urls)),
]
