from django.urls import path

from Apps.views.Otome.panel import (
    assets_view,
    data_list,
    game_edit,
    game_list,
    login_view,
    logout_view,
    node_edit,
    user_list,
    ads_view,
)

urlpatterns = [
    path("login/", login_view, name="otome-panel-login"),
    path("logout/", logout_view, name="otome-panel-logout"),
    path("", game_list, name="otome-panel-games"),
    path("data/", data_list, name="otome-panel-data"),
    path("users/", user_list, name="otome-panel-users"),
    path("ads/", ads_view, name="otome-panel-ads"),
    path("assets/", assets_view, name="otome-panel-assets"),
    path("games/<int:game_id>/", game_edit, name="otome-panel-game"),
    path("games/<int:game_id>/nodes/new/", node_edit, name="otome-panel-node-new"),
    path("games/<int:game_id>/nodes/<int:node_id>/", node_edit, name="otome-panel-node"),
]
