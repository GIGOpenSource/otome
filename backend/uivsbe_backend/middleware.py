# template/middleware.py（和 settings.py 同级目录）
from django.http import JsonResponse


class CorsMiddleware:
    """让 H5 客户端可以请求接口并下载媒体文件。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = JsonResponse({"code": 200, "message": "ok", "results": {}})
        else:
            response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Expose-Headers"] = "*"
        response["Access-Control-Max-Age"] = "86400"
        return response


class OtomeLocaleMiddleware:
    """按显式语言头、落地页参数、cookie 或浏览器语言切换文案。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from Apps.views.Otome.i18n import activate, resolve_lang

        lang = activate(resolve_lang(request))
        request.otome_lang = lang
        response = self.get_response(request)
        if request.GET.get("lang"):
            response.set_cookie("otome_lang", lang, max_age=365 * 24 * 3600, samesite="Lax")
        response["Content-Language"] = lang
        return response


class DummyUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 给 request 加一个 dummy user，仅满足 rosetta 的属性检查
        class DummyUser:
            is_authenticated = True  # 模拟已登录
            is_staff = True  # 模拟 staff 权限（rosetta 要求）
            is_superuser = True  # 模拟超级用户权限

        request.user = DummyUser()  # 给 request 绑定 user 属性
        response = self.get_response(request)
        return response