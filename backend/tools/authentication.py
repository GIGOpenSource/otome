# tools/authentication.py
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed

from django.utils.translation import gettext_lazy as _

from models.models import User
from tools.password_hasher import verify_password
from tools.token_tools import CustomTokenTool, generate_is_user_token
from tools.auth_helpers import get_token_from_request


class CustomBasicAuthentication(BasicAuthentication):
    """
    完全重写 BasicAuthentication，使用自定义的密码验证逻辑 应用到swaggerui
    """
    def authenticate_credentials(self, userid, password, request=None):
        try:
            user = User.objects.get(username=userid)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=userid)
            except User.DoesNotExist:
                raise AuthenticationFailed(_('无效的用户名或密码'))
        if not verify_password(password, user.password):
            raise AuthenticationFailed(_('无效的用户名或密码'))
        token = generate_is_user_token(request, user)
        return (user, token)

    def authenticate_header(self, request):
        return 'Basic realm="%s"' % self.www_authenticate_realm


from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CustomBasicAuthSchema(OpenApiAuthenticationExtension):
    target_class = 'tools.authentication.CustomBasicAuthentication'
    name = 'CustomBasicAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'basic',
            'description': "使用用户名/密码登录（密码验证逻辑：截断72字节后验证）"
        }


class TokenAuthentication(BasicAuthentication):
    """
    基于Token的认证：支持 token 请求头、Authorization、Cookie
    无效token不抛异常，交由 permission 层控制访问权限
    """
    def authenticate(self, request):
        token = get_token_from_request(request)
        if not token:
            return None

        is_valid, user_id = CustomTokenTool.verify_token(token)
        if not is_valid or not user_id:
            return None  # 无效token视为未认证，不抛异常

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

        return (user, token)

    def authenticate_header(self, request):
        return 'Token realm="API"'


class TokenAuthSchema(OpenApiAuthenticationExtension):
    target_class = 'tools.authentication.TokenAuthentication'
    name = 'TokenAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'token',
            'description': '通过token进行认证，支持 header: token / Authorization: Token xxx / Cookie'
        }
