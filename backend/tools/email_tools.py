#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
邮箱验证码工具
"""
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.utils.translation import gettext as _
from tools.token_tools import _redis


# 邮箱配置
EMAIL_HOST = "smtp.163.com"
EMAIL_PORT = 465
EMAIL_USER = "17502413556@163.com"
EMAIL_PASSWORD = "GZtj532yzQyPpDnw"
EMAIL_FROM = "BuildMart <17502413556@163.com>"

# 验证码配置
VERIFY_CODE_LENGTH = 6
VERIFY_CODE_EXPIRE_SECONDS = 300

# Redis key 前缀
REDIS_EMAIL_CODE_PREFIX = "EmailVerifyCode:"


def generate_verify_code(length=VERIFY_CODE_LENGTH):
    """生成数字验证码"""
    return ''.join(random.choices(string.digits, k=length))


def get_existing_verify_code(email, scene="register"):
    """
    获取已存在的未过期验证码
    :param email: 邮箱
    :param scene: 场景
    :return: 已存在的验证码，不存在则返回 None
    """
    key = f"{REDIS_EMAIL_CODE_PREFIX}{scene}:{email}"
    code = _redis.getKey(key)
    # 统一转为字符串（Redis可能返回bytes）
    if code and isinstance(code, bytes):
        return code.decode('utf-8')
    return code


def save_verify_code(email, code, scene="register"):
    """
    保存验证码到 Redis
    :param email: 邮箱
    :param code: 验证码
    :param scene: 场景 (register/reset_password)
    """
    key = f"{REDIS_EMAIL_CODE_PREFIX}{scene}:{email}"
    _redis.setKey(key, code, ex=VERIFY_CODE_EXPIRE_SECONDS)
    return True


def verify_code(email, code, scene="register"):
    """
    验证邮箱验证码
    :param email: 邮箱
    :param code: 验证码
    :param scene: 场景
    :return: (是否成功, 错误信息)
    """
    key = f"{REDIS_EMAIL_CODE_PREFIX}{scene}:{email}"
    stored_code = _redis.getKey(key)

    if not stored_code:
        return False, _("验证码已过期或不存在")

    # 统一转为字符串比较（Redis可能返回bytes或str）
    if isinstance(stored_code, bytes):
        stored_code = stored_code.decode('utf-8')

    if str(stored_code).strip() != str(code).strip():
        return False, _("验证码错误")

    # 验证成功后删除验证码
    _redis.delKey(key)
    return True, None


def delete_verify_code(email, scene="register"):
    """删除验证码"""
    key = f"{REDIS_EMAIL_CODE_PREFIX}{scene}:{email}"
    _redis.delKey(key)
    return True


def send_verify_email(to_email, code, scene="register"):
    """
    发送验证码邮件
    :param to_email: 收件人邮箱
    :param code: 验证码
    :param scene: 场景
    :return: (是否成功, 错误信息)
    """
    # 根据场景设置邮件内容
    if scene == "register":
        subject = "【BuildMart】注册验证码"
        body = f"""
        <html>
        <body>
            <h2>BuildMart 注册验证码</h2>
            <p>您好！您正在注册 BuildMart 账号。</p>
            <p>您的验证码是：<strong style="font-size: 24px; color: #1890ff;">{code}</strong></p>
            <p>验证码 {VERIFY_CODE_EXPIRE_SECONDS // 60} 分钟内有效，请勿泄露给他人。</p>
            <p>如非本人操作，请忽略此邮件。</p>
            <br>
            <p>BuildMart 团队</p>
        </body>
        </html>
        """
    elif scene == "reset_password":
        subject = "【BuildMart】重置密码验证码"
        body = f"""
        <html>
        <body>
            <h2>BuildMart 重置密码验证码</h2>
            <p>您好！您正在重置 BuildMart 账号密码。</p>
            <p>您的验证码是：<strong style="font-size: 24px; color: #1890ff;">{code}</strong></p>
            <p>验证码 {VERIFY_CODE_EXPIRE_SECONDS // 60} 分钟内有效，请勿泄露给他人。</p>
            <p>如非本人操作，请忽略此邮件。</p>
            <br>
            <p>BuildMart 团队</p>
        </body>
        </html>
        """
    else:
        subject = "【BuildMart】邮箱验证码"
        body = f"""
        <html>
        <body>
            <h2>BuildMart 邮箱验证码</h2>
            <p>您的验证码是：<strong style="font-size: 24px; color: #1890ff;">{code}</strong></p>
            <p>验证码 {VERIFY_CODE_EXPIRE_SECONDS // 60} 分钟内有效，请勿泄露给他人。</p>
            <br>
            <p>BuildMart 团队</p>
        </body>
        </html>
        """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email

        html_part = MIMEText(body, 'html', 'utf-8')
        msg.attach(html_part)

        # 使用 SSL 连接
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, [to_email], msg.as_string())

        return True, None
    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
        if "SMTPRecipientsRefused" in str(type(e)) or "User not found" in str(e):
            return False, _("邮箱不存在，请检查邮箱地址是否正确")
        return False, _("邮件发送失败，请稍后重试")
