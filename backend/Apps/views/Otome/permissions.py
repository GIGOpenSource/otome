import logging

from django.conf import settings
from django.core import signing
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

STAFF_SALT = "otome-staff"
STAFF_AGE = 60 * 60 * 24 * 7
STAFF_ROLES = ("operator", "admin", "super_admin")


def issue_staff_token(user):
    return signing.dumps({"uid": user.id}, salt=STAFF_SALT)


def staff_from_token(token):
    if not token:
        return None
    try:
        data = signing.loads(token, salt=STAFF_SALT, max_age=STAFF_AGE)
    except Exception:
        return None
    try:
        from models.models import User

        user = User.objects.get(id=data.get("uid"))
    except Exception:
        return None
    if user.status == 1 and user.role in STAFF_ROLES:
        return user
    return None


def _user_from_auth_token(request):
    try:
        from models.models import User
        from tools.auth_helpers import get_token_from_request
        from tools.token_tools import CustomTokenTool
    except Exception:
        logger.error("加载认证模块失败", exc_info=True)
        return None
    token = get_token_from_request(request)
    if not token:
        return None
    try:
        is_valid, user_id = CustomTokenTool.verify_token(token)
    except Exception:
        logger.warning("校验管理员 token 失败", exc_info=True)
        return None
    if not is_valid or not user_id:
        return None
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None
    if user.status == 1 and user.role in STAFF_ROLES:
        return user
    return None


def current_staff(request):
    """当前后台账号。管理密钥没有对应账号，返回 None。"""
    if getattr(request, "_otome_staff_resolved", False):
        return getattr(request, "_otome_staff", None)
    request._otome_staff_resolved = True
    user = staff_from_token(request.headers.get("token", ""))
    if user is None:
        user = _user_from_auth_token(request)
    request._otome_staff = user
    return user


def admin_key_matches(request):
    key = request.headers.get("X-Otome-Key", "")
    expected = getattr(settings, "OTOME_ADMIN_KEY", "otome-demo")
    return bool(key and key == expected)


def sees_all_games(request):
    """超管和管理密钥可以看全部游戏。其余后台账号看自己创建的和被分配的。"""
    user = current_staff(request)
    if user is not None:
        return user.role == "super_admin"
    return admin_key_matches(request)


def visible_games(request):
    """超管看全部。其他账号看自己创建的，以及超管划给自己的游戏。"""
    from django.db.models import Q
    from models.models import OtomeGame

    queryset = OtomeGame.objects.filter(is_deleted=False)
    if sees_all_games(request):
        return queryset
    user = current_staff(request)
    if user is None:
        return queryset.none()
    return queryset.filter(Q(created_by=user) | Q(staff_links__user=user)).distinct()


def scope_to_visible_games(queryset, request, relation="game"):
    if sees_all_games(request):
        return queryset
    if current_staff(request) is None:
        return queryset.none()
    if not relation:
        return queryset.filter(created_by=current_staff(request))
    return queryset.filter(**{f"{relation}__in": visible_games(request)})


def ensure_game_access(request, game):
    from rest_framework.exceptions import ValidationError

    if game is None:
        return
    if not getattr(game, "is_deleted", False) and visible_games(request).filter(pk=game.pk).exists():
        return
    raise ValidationError("不能操作这部游戏")


class IsOtomeAdmin(BasePermission):
    """后台用户名密码登录后的会话。玩家拉脚本不走这个权限。"""

    message = "请先登录后台"

    def has_permission(self, request, view):
        if current_staff(request):
            return True
        return admin_key_matches(request)
