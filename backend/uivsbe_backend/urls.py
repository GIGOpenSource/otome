"""
URL configuration for template project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.http import JsonResponse

from Apps.views.Otome.landing import game_landing, game_landing_download, landing_download, landing_page
from tools.uploader_data import UploadResourceView


# 简单的根路径处理函数
def home(request):
    return JsonResponse({"message": "Welcome to BuildMart API", "version": "1.0.0"})

urlpatterns = [
    # 根路径
    path('', home, name='home'),
    # 业务接口（无语言前缀）
    path('api/', include('Apps.urls')),
    # 文档路由
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/upload/', UploadResourceView.as_view(), name='upload_resource'),
    path('otome-admin/', include('Apps.views.Otome.panel_urls')),
    path('land/<int:game_id>/', game_landing, name='otome-game-landing'),
    path('land/<int:game_id>/<str:store>/', game_landing_download, name='otome-game-landing-download'),
    path('go/<str:channel_id>/', landing_page, name='otome-landing'),
    path('go/<str:channel_id>/<str:store>/', landing_download, name='otome-landing-download'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)