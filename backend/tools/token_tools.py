#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：BuildMart
@File    ：tool_tools.py
@Author  ：Lianghaibo
@Date    ：2026/5/28 23:10
@description :
"""
import redis
import base64
import time
from datetime import timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from tools.tools import getEnvConfig


# -------------------------- 全局配置项 --------------------------
# AES 密钥
AES_SECRET_KEY = getEnvConfig("OTOME_TOKEN_KEY", "change-me-16chars").encode("utf-8")
# 登录Token过期时长(小时)
TOKEN_EXPIRE_HOURS = 2
# 聊天房间Token过期时长(小时)，可单独配置
ROOM_TOKEN_EXPIRE_HOURS = 4
# AES 固定IV长度
AES_IV_LENGTH = 16

# Redis 命名空间（模拟文件夹，按业务隔离）
REDIS_LOGIN_PREFIX = "Login:"    # 登录令牌目录
REDIS_CHAT_PREFIX = "ChatRoom:" # 聊天房间令牌目录


class RedisTool(object):
    """redis 工具类"""
    def __init__(self):
        self.host = getEnvConfig("REDIS_BUILDMART_HOST", "localhost")
        self.port = int(getEnvConfig("REDIS_PORT", 6389))
        self.password = getEnvConfig("REDIS_BUILDMART_PASSWORD", "")
        self.db = int(getEnvConfig("REDIS_DB", 0))
        self.ex = 3600
        max_connections = getEnvConfig("REDIS_MAX_CONNECTIONS", 10)
        try:
            max_connections = int(max_connections)
            if max_connections <= 0:
                raise ValueError("max_connections 必须是正整数")
        except (ValueError, TypeError):
            raise ValueError("max_connections 必须是正整数")

        self.pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db,
            max_connections=max_connections
        )
        self.client = redis.Redis(connection_pool=self.pool, decode_responses=True)

    def setKey(self, key, values, ex=None):
        """支持自定义过期时间"""
        expire = ex if ex else self.ex
        self.client.set(key, values, ex=expire)
        return True

    def getKey(self, key):
        return self.client.get(key)

    def delKey(self, key):
        self.client.delete(key)
        return True

    def expireKey(self, key, ex=None):
        expire = ex if ex else self.ex
        self.client.expire(key, expire)


_redis = RedisTool()


class CustomTokenTool:
    @staticmethod
    def _aes_encrypt(data: bytes) -> tuple[bytes, bytes]:
        """AES 加密：返回(加密数据, IV)"""
        iv = get_random_bytes(AES_IV_LENGTH)
        cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(data, AES.block_size))
        return encrypted_data, iv

    @staticmethod
    def _aes_decrypt(encrypted_data: bytes, iv: bytes) -> bytes:
        """AES 解密"""
        cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        return decrypted_data

    # ====================== 登录 Token 原有逻辑（无改动）======================
    @classmethod
    def generate_token(cls, user_id: int, remember: bool = False) -> str:
        """生成用户登录Token"""
        expire_timestamp = int(time.time()) + int(timedelta(hours=TOKEN_EXPIRE_HOURS).total_seconds())
        token_core = f"{user_id}:{expire_timestamp}".encode("utf-8")
        encrypted_core, iv = cls._aes_encrypt(token_core)
        token_bytes = iv + encrypted_core

        raw_token = base64.b64encode(token_bytes).decode("utf-8")
        token = f"{REDIS_LOGIN_PREFIX}{raw_token}"
        expire_seconds = int(timedelta(days=30 if remember else 7).total_seconds())
        _redis.setKey(token, user_id, ex=expire_seconds)
        return token

    @classmethod
    def verify_token(cls, token: str) -> tuple[bool, int | None]:
        """校验登录Token"""
        try:
            if not token:
                return False, None
            # 兼容旧 token（无 Login: 前缀）
            redis_key = token if token.startswith(REDIS_LOGIN_PREFIX) else f"{REDIS_LOGIN_PREFIX}{token}"
            user_id_str = _redis.getKey(redis_key)
            if not user_id_str:
                return False, None
            _redis.expireKey(redis_key)
            return True, int(user_id_str)
        except Exception as e:
            print(f"Token 校验失败：{str(e)}")
            return False, None

    @classmethod
    def delete_token(cls, token):
        """删除登录Token（登出）"""
        if not token:
            return
        redis_key = token if str(token).startswith(REDIS_LOGIN_PREFIX) else f"{REDIS_LOGIN_PREFIX}{token}"
        _redis.delKey(redis_key)

    @classmethod
    def delete_user_all_tokens(cls, user_id: int):
        """
        删除某个用户的所有登录 Token（挤下线）
        """
        try:
            # 找到 Login: 下所有属于这个 user_id 的 token
            keys = _redis.client.keys(f"{REDIS_LOGIN_PREFIX}*")
            for key in keys:
                val = _redis.getKey(key)
                if val and str(val) == str(user_id):
                    _redis.delKey(key)
            return True
        except Exception as e:
            print("删除旧token失败", e)
            return False

    # ====================== 新增：聊天房间 Token 逻辑 ======================
    @classmethod
    def generate_room_token(cls, room_id: str | int) -> str:
        """
        生成聊天房间Token
        :param room_id: 聊天室ID/房间号
        :return: RoomToken:xxx 格式令牌
        """
        expire_timestamp = int(time.time()) + int(timedelta(hours=ROOM_TOKEN_EXPIRE_HOURS).total_seconds())
        # 数据格式：房间号:过期时间
        token_core = f"{room_id}:{expire_timestamp}".encode("utf-8")
        encrypted_core, iv = cls._aes_encrypt(token_core)
        token_bytes = iv + encrypted_core

        raw_token = base64.b64encode(token_bytes).decode("utf-8")
        room_token = f"RoomToken:{raw_token}"
        # Redis 键：ChatRoom:RoomToken:xxx
        redis_key = f"{REDIS_CHAT_PREFIX}{room_token}"
        # 存入房间ID，使用房间专属过期时间
        _redis.setKey(redis_key, str(room_id), ex=int(timedelta(hours=ROOM_TOKEN_EXPIRE_HOURS).total_seconds()))
        return room_token

    @classmethod
    def verify_room_token(cls, room_token: str) -> tuple[bool, str | None]:
        """
        校验聊天房间Token
        :param room_token: 前端传入的房间令牌
        :return: (是否有效, 房间号)
        """
        try:
            if not room_token or not room_token.startswith("RoomToken:"):
                return False, None
            redis_key = f"{REDIS_CHAT_PREFIX}{room_token}"
            room_id = _redis.getKey(redis_key)
            if not room_id:
                return False, None
            # 续期房间Token
            _redis.expireKey(redis_key, ex=int(timedelta(hours=ROOM_TOKEN_EXPIRE_HOURS).total_seconds()))
            return True, room_id
        except Exception as e:
            print(f"房间Token 校验失败：{str(e)}")
            return False, None

    @classmethod
    def delete_room_token(cls, room_token: str):
        """销毁房间Token（关闭房间/退出聊天）"""
        if room_token and room_token.startswith("RoomToken:"):
            redis_key = f"{REDIS_CHAT_PREFIX}{room_token}"
            _redis.delKey(redis_key)


"""
是否生成登录token，如果已有有效token则复用
"""
def generate_is_user_token(request, user):
    if request:
        existing_token = 0
        if existing_token:
            is_valid, user_id = CustomTokenTool.verify_token(existing_token)
            if is_valid and user_id == user.id:
                return existing_token
    token = CustomTokenTool.generate_token(user.id)
    if request:
        print(1)
    return token

def generate_login_user_token(request, user, remember=False):
    # ====================== 登录 删旧token ======================
    CustomTokenTool.delete_user_all_tokens(user.id)

    # 然后生成新 token
    token = CustomTokenTool.generate_token(user.id, remember=remember)
    return token