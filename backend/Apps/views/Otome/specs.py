"""图片尺寸标准。后台配置和上传校验都用这一份。"""

IMAGE_SPECS = (
    {
        "usage": "background",
        "screen": "portrait",
        "title": "竖屏背景",
        "width": 1080,
        "height": 1920,
        "ratio": "9:16",
        "note": "全屏铺满。人物和关键景物放在中间，底部约 420px 会被对话框挡住。",
    },
    {
        "usage": "background",
        "screen": "landscape",
        "title": "横屏背景",
        "width": 1920,
        "height": 1080,
        "ratio": "16:9",
        "note": "全屏铺满。关键景物放在中间，底部约 220px 会被对话框挡住。",
    },
    {
        "usage": "character",
        "screen": "portrait",
        "title": "竖屏立绘",
        "width": 1080,
        "height": 1920,
        "ratio": "9:16",
        "note": "透明 PNG。人物居中，脚底贴着画布底边。",
    },
    {
        "usage": "character",
        "screen": "landscape",
        "title": "横屏立绘",
        "width": 1920,
        "height": 1080,
        "ratio": "16:9",
        "note": "透明 PNG。人物放在画面右侧，脚底贴着画布底边。",
    },
    {
        "usage": "cover",
        "screen": "portrait",
        "title": "竖屏封面",
        "width": 1080,
        "height": 1920,
        "ratio": "9:16",
        "note": "标题页竖屏使用，重要内容避开四边 80px。",
    },
    {
        "usage": "cover",
        "screen": "landscape",
        "title": "横屏封面",
        "width": 1920,
        "height": 1080,
        "ratio": "16:9",
        "note": "标题页横屏使用，重要内容避开四边 80px。",
    },
)


def find_spec(usage, screen):
    for spec in IMAGE_SPECS:
        if spec["usage"] == usage and spec["screen"] == screen:
            return spec
    return None


def size_text(usage, screen):
    spec = find_spec(usage, screen)
    if spec is None:
        return ""
    return f"{spec['width']} × {spec['height']}（{spec['ratio']}）"


def asset_label(name, usage, screen):
    spec = find_spec(usage, screen)
    if spec is None:
        return f"{name} · 未标注尺寸"
    return f"{name} · {spec['title']} {spec['width']}×{spec['height']}"


def check_upload_size(upload, usage, screen):
    """上传的图片必须和所选用途、方向的像素完全一致。"""
    spec = find_spec(usage, screen)
    if spec is None:
        raise ValueError("图片必须选择用途和横竖屏")
    name = getattr(upload, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == "svg":
        raise ValueError(f"{spec['title']}请上传 {spec['width']}×{spec['height']} 的 png、jpg、webp 或 gif")
    try:
        from PIL import Image
    except Exception:
        raise ValueError("服务器还不能读取图片尺寸")
    position = upload.tell()
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            width, height = image.size
    except Exception:
        raise ValueError("无法读取图片尺寸，请上传 png、jpg、webp 或 gif")
    finally:
        upload.seek(position)
    if width != spec["width"] or height != spec["height"]:
        raise ValueError(
            f"{spec['title']}必须是 {spec['width']}×{spec['height']} 像素，当前是 {width}×{height}"
        )
    return spec
