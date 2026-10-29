#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""登录态持久化：Cookie + Header"""
from datetime import timedelta

from tools.token_tools import TOKEN_EXPIRE_HOURS

# Cookie 默认 7 天；勾选「记住我」30 天
SESSION_EXPIRE_SECONDS = int(timedelta(days=7).total_seconds())
REMEMBER_EXPIRE_SECONDS = int(timedelta(days=30).total_seconds())
COOKIE_NAME = 'auth_token'


def get_token_from_request(request) -> str | None:
    """从请求中提取 token（header / Authorization / cookie）"""
    token = request.headers.get('token')
    if token:
        return token.strip()

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Token '):
        return auth_header[6:].strip()
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()

    token = request.COOKIES.get(COOKIE_NAME)
    if token:
        return token.strip()

    return None


def persist_auth(request, response, token: str, user_id: int, remember: bool = False):
    """登录成功后写入 Cookie"""
    max_age = REMEMBER_EXPIRE_SECONDS if remember else SESSION_EXPIRE_SECONDS

    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=False,
        samesite='Lax',
        secure=False,
    )
    return response


def clear_auth(request, response):
    """登出时清除 Cookie"""
    response.delete_cookie(COOKIE_NAME)
    return response


def token_redis_expire(remember: bool = False) -> int:
    """Redis 中 token 过期秒数"""
    if remember:
        return REMEMBER_EXPIRE_SECONDS
    return int(timedelta(hours=TOKEN_EXPIRE_HOURS).total_seconds())
