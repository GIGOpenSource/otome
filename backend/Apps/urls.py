#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：UIVSBE
@File    ：urls.py
@Author  ：AI Assistant
@Date    ：2026/08/06
@description : 应用路由配置
"""
from django.urls import path, include
from rest_framework import routers

from Apps.views.user.view import UserViewSet, AdminUserViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    path('', include(router.urls)),
    # 管理员认证模块
    path('admin/', include('Apps.views.admin.urls')),
    # 示例管理模块
    path('example/', include('Apps.views.Example.urls')),
    # 乙游：素材、故事、给单游戏客户端拉取的脚本
    path('otome/', include('Apps.views.Otome.urls')),
]
