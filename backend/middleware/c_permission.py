from rest_framework.permissions import BasePermission

from models.models import User
from tools.token_tools import CustomTokenTool
from tools.auth_helpers import get_token_from_request


class IsTokenValid(BasePermission):
    """
    自定义权限：仅允许携带有效 Token 的请求访问
    """
    message = "Token 无效或已过期"

    def has_permission(self, request, view):
        token = get_token_from_request(request)
        if not token:
            return False

        is_valid, user_id = CustomTokenTool.verify_token(token)
        if not is_valid or not user_id:
            return False

        try:
            request.user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return False
        return True
