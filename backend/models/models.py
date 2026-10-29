from django.db import models
from tools.password_hasher import hash_password


class User(models.Model):
    """用户表"""
    username = models.CharField(max_length=20, unique=True, verbose_name="用户名")
    email = models.EmailField(unique=True, verbose_name="邮箱")
    password = models.CharField(max_length=256, verbose_name="密码")
    role = models.CharField(max_length=20, default="user", verbose_name="角色")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    status = models.IntegerField(default=1, verbose_name="状态")  # 1: 正常, 0: 禁用
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def save(self, *args, **kwargs):
        if not self.password.startswith('$2b$'):
            self.password = hash_password(self.password[:72])
        super().save(*args, **kwargs)

    class Meta:
        db_table = 't_user'
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.username


class Example(models.Model):
    """示例表 — 建表规范参考，表名以 t_ 开头"""

    STATUS_DRAFT = 0
    STATUS_ACTIVE = 1
    STATUS_DISABLED = 2
    STATUS_CHOICES = [
        (STATUS_DRAFT, '草稿'),
        (STATUS_ACTIVE, '启用'),
        (STATUS_DISABLED, '禁用'),
    ]

    name = models.CharField(max_length=100, verbose_name="名称")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    status = models.IntegerField(default=STATUS_ACTIVE, choices=STATUS_CHOICES, verbose_name="状态")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    remark = models.CharField(max_length=500, null=True, blank=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 't_example'
        verbose_name = "示例"
        verbose_name_plural = "示例"
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.name


class OtomeAsset(models.Model):
    """图片、音频或视频。故事只保存引用，替换素材就会换掉所有用到它的画面和声音。"""

    TYPE_IMAGE = "image"
    TYPE_AUDIO = "audio"
    TYPE_VIDEO = "video"
    TYPE_CHOICES = (
        (TYPE_IMAGE, "图片"),
        (TYPE_AUDIO, "音频"),
        (TYPE_VIDEO, "视频"),
    )
    USAGE_BACKGROUND = "background"
    USAGE_CHARACTER = "character"
    USAGE_COVER = "cover"
    USAGE_CHOICES = (
        (USAGE_BACKGROUND, "背景"),
        (USAGE_CHARACTER, "立绘"),
        (USAGE_COVER, "封面"),
    )
    SCREEN_PORTRAIT = "portrait"
    SCREEN_LANDSCAPE = "landscape"
    SCREEN_CHOICES = (
        (SCREEN_PORTRAIT, "竖屏"),
        (SCREEN_LANDSCAPE, "横屏"),
    )

    game = models.ForeignKey(
        "OtomeGame", null=True, blank=True, on_delete=models.CASCADE,
        related_name="assets", verbose_name="所属游戏",
    )
    name = models.CharField(max_length=100, verbose_name="名称")
    asset_type = models.CharField(max_length=16, choices=TYPE_CHOICES, verbose_name="类型")
    usage = models.CharField(max_length=16, blank=True, default="", choices=USAGE_CHOICES, verbose_name="画面用途")
    screen = models.CharField(max_length=16, blank=True, default="", choices=SCREEN_CHOICES, verbose_name="屏幕方向")
    file = models.FileField(upload_to="otome/assets/", blank=True, default="", verbose_name="文件")
    url = models.CharField(max_length=1000, blank=True, default="", verbose_name="外链地址", help_text="填写后优先使用外链")
    duration = models.FloatField(
        null=True, blank=True, verbose_name="时长",
        help_text="音频时长，单位秒。图片和视频为空",
    )
    file_size = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="大小",
        help_text="文件字节数",
    )
    remark = models.CharField(max_length=200, blank=True, default="", verbose_name="备注")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_asset"
        verbose_name = "乙游素材"
        verbose_name_plural = "乙游素材"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["game", "is_deleted", "-id"], name="otome_asset_game_alive"),
        ]

    def __str__(self):
        return self.name

    @property
    def standard_label(self):
        from Apps.views.Otome.specs import asset_label
        if self.asset_type != self.TYPE_IMAGE:
            return self.name
        return asset_label(self.name, self.usage, self.screen)


class OtomeGame(models.Model):
    """一部乙游。后台发布一部，再把游戏 ID 配进单独的客户端，就是一款新游戏。"""

    STATUS_DRAFT = 0
    STATUS_PUBLISHED = 1
    STATUS_CHOICES = (
        (STATUS_DRAFT, "草稿"),
        (STATUS_PUBLISHED, "已发布"),
    )

    code = models.CharField(max_length=64, unique=True, null=True, blank=True, verbose_name="故事编码")
    title = models.CharField(max_length=100, verbose_name="标题")
    subtitle = models.CharField(max_length=200, blank=True, default="", verbose_name="副标题")
    summary = models.TextField(blank=True, default="", verbose_name="简介")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    cover = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="cover_games", verbose_name="竖屏封面",
    )
    cover_land = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="cover_land_games", verbose_name="横屏封面",
    )
    splash_url = models.CharField(
        max_length=500, blank=True, default="", verbose_name="开屏竖屏",
        help_text="进入游戏时先显示的竖屏开屏图。可存上传后的网址，也可由素材编号换算",
    )
    splash_land_url = models.CharField(
        max_length=500, blank=True, default="", verbose_name="开屏横屏",
        help_text="进入游戏时先显示的横屏开屏图。可存上传后的网址，也可由素材编号换算",
    )
    play_package = models.CharField(
        max_length=120, blank=True, default="", verbose_name="Google 包名",
        help_text="落地页的 Google Play 下载按钮使用，例如 com.example.game",
    )
    ios_app_id = models.CharField(
        max_length=32, blank=True, default="", verbose_name="App Store ID",
        help_text="落地页的 iOS 下载按钮使用，只填数字",
    )
    frontend_url = models.CharField(
        max_length=500, blank=True, default="", verbose_name="进入游戏",
        help_text="玩家直接打开并游玩的地址。留空时，本机有对应客户端就用开发地址",
    )
    landing_url = models.CharField(
        max_length=500, blank=True, default="", verbose_name="落地页",
        help_text="下载页地址，和进入游戏不是同一个链接。留空时使用 /land/游戏ID/",
    )
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_games", verbose_name="创建人",
    )
    status = models.IntegerField(default=STATUS_DRAFT, choices=STATUS_CHOICES, verbose_name="状态")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_game"
        verbose_name = "乙游故事"
        verbose_name_plural = "乙游故事"
        ordering = ["sort_order", "-id"]

    def __str__(self):
        return self.title


class OtomeCharacter(models.Model):
    game = models.ForeignKey(OtomeGame, on_delete=models.CASCADE, related_name="characters", verbose_name="所属故事")
    name = models.CharField(max_length=50, verbose_name="姓名")
    title = models.CharField(max_length=100, blank=True, default="", verbose_name="身份")
    portrait = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="portrait_characters", verbose_name="竖屏立绘",
    )
    portrait_land = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="portrait_land_characters", verbose_name="横屏立绘",
    )
    name_color = models.CharField(max_length=20, blank=True, default="#e7c27a", verbose_name="名字颜色")
    intro = models.TextField(blank=True, default="", verbose_name="介绍")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_character"
        verbose_name = "乙游角色"
        verbose_name_plural = "乙游角色"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class OtomeCharacterImage(models.Model):
    """一个角色可以有很多张立绘。剧情里每次出场再从这里挑。"""

    character = models.ForeignKey(OtomeCharacter, on_delete=models.CASCADE, related_name="images", verbose_name="角色")
    label = models.CharField(max_length=50, blank=True, default="", verbose_name="名称")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    image = models.ForeignKey(
        OtomeAsset, on_delete=models.CASCADE, related_name="character_images", verbose_name="竖屏图",
    )
    image_land = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="character_images_land", verbose_name="横屏图",
    )
    screen_size = models.PositiveSmallIntegerField(
        default=100, verbose_name="占据画面的大小",
        help_text="立绘占画面的百分比，100 为铺满所在位置",
    )
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_character_image"
        verbose_name = "角色立绘"
        verbose_name_plural = "角色立绘"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.label or str(self.image_id)


class OtomeNode(models.Model):
    """一句剧情。关键节点会让客户端先下载这一段的图片和音频，再进入。"""

    game = models.ForeignKey(OtomeGame, on_delete=models.CASCADE, related_name="nodes", verbose_name="所属故事")
    node_key = models.CharField(max_length=64, verbose_name="剧情编号")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    character = models.ForeignKey(
        OtomeCharacter, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="lines", verbose_name="说话角色",
    )
    speaker_name = models.CharField(max_length=50, blank=True, default="", verbose_name="显示名", help_text="留空则使用角色名")
    content = models.TextField(verbose_name="对白")
    background = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="background_nodes", verbose_name="竖屏背景",
    )
    background_land = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="background_land_nodes", verbose_name="横屏背景",
    )
    portrait = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="portrait_nodes", verbose_name="竖屏立绘",
    )
    portrait_land = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="portrait_land_nodes", verbose_name="横屏立绘",
    )
    bgm = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="bgm_nodes", verbose_name="背景音乐",
    )
    voice = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="voice_nodes", verbose_name="语音",
    )
    interact = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="interact_nodes", verbose_name="交互音频",
        help_text="玩家点击这段对白时播放一次",
    )
    insert_media = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="insert_nodes", verbose_name="结束后插入",
        help_text="这段对白结束后全屏播放，可以是视频或图片",
    )
    insert_title = models.CharField(
        max_length=100, blank=True, default="", verbose_name="解锁标题",
        help_text="留空则使用素材名称。看过或跳过后出现在故事解锁里",
    )
    next_node = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="previous_nodes", verbose_name="下一句",
    )
    is_start = models.BooleanField(default=False, verbose_name="开场")
    is_key = models.BooleanField(default=False, verbose_name="关键节点", help_text="进入前下载本段图片和音频")
    is_ending = models.BooleanField(default=False, verbose_name="结局")
    ending_title = models.CharField(max_length=100, blank=True, default="", verbose_name="结局标题")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    CAST_SINGLE = "single"
    CAST_MULTI = "multi"
    CAST_CHOICES = (
        (CAST_SINGLE, "单角色"),
        (CAST_MULTI, "多角色"),
    )
    cast_mode = models.CharField(
        max_length=8, choices=CAST_CHOICES, default=CAST_SINGLE, verbose_name="画面人数",
        help_text="单角色只显示一个，多角色可以同时站在不同位置",
    )
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_node"
        verbose_name = "乙游剧情"
        verbose_name_plural = "乙游剧情"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "node_key"],
                condition=models.Q(is_deleted=False),
                name="uniq_otome_node_key_alive",
            )
        ]

    def __str__(self):
        return self.node_key


class OtomeNodeFigure(models.Model):
    """这一句画面上的一个角色，以及他站的位置。"""

    POSITIONS = (
        ("nw", "左上"), ("n", "上"), ("ne", "右上"),
        ("w", "左"), ("c", "中"), ("e", "右"),
        ("sw", "左下"), ("s", "下"), ("se", "右下"),
    )

    node = models.ForeignKey(OtomeNode, on_delete=models.CASCADE, related_name="figures", verbose_name="剧情")
    character = models.ForeignKey(
        OtomeCharacter, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="figures", verbose_name="角色",
    )
    image = models.ForeignKey(
        OtomeCharacterImage, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="figures", verbose_name="立绘",
    )
    position = models.CharField(max_length=8, choices=POSITIONS, default="c", verbose_name="位置")
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "t_otome_node_figure"
        verbose_name = "画面角色"
        verbose_name_plural = "画面角色"
        ordering = ["sort_order", "id"]


class OtomeChoice(models.Model):
    node = models.ForeignKey(OtomeNode, on_delete=models.CASCADE, related_name="choices", verbose_name="所在剧情")
    text = models.CharField(max_length=200, verbose_name="选项文字")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    next_node = models.ForeignKey(
        OtomeNode, on_delete=models.CASCADE, related_name="incoming_choices", verbose_name="跳转剧情",
    )
    interact = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="interact_choices", verbose_name="交互音频",
        help_text="玩家点这个选项时播放一次",
    )
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_choice"
        verbose_name = "乙游选项"
        verbose_name_plural = "乙游选项"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.text


class OtomePlayer(models.Model):
    """前端玩家。设备号会生成一个 UID，也可以改用 Google 账号登录。"""

    LOGIN_DEVICE = "device"
    LOGIN_GOOGLE = "google"
    LOGIN_CHOICES = (
        (LOGIN_DEVICE, "设备快速登录"),
        (LOGIN_GOOGLE, "Google"),
    )

    uid = models.CharField(max_length=16, unique=True, verbose_name="UID")
    device_id = models.CharField(max_length=128, blank=True, default="", db_index=True, verbose_name="设备号")
    google_sub = models.CharField(max_length=128, blank=True, default="", db_index=True, verbose_name="Google 账号")
    email = models.EmailField(blank=True, default="", verbose_name="邮箱")
    nickname = models.CharField(max_length=64, blank=True, default="", verbose_name="昵称")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    login_type = models.CharField(max_length=16, choices=LOGIN_CHOICES, default=LOGIN_DEVICE, verbose_name="登录方式")
    channel = models.ForeignKey(
        "OtomeAdChannel", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="players", verbose_name="来源渠道",
        help_text="第一次从某条用户来源进来时记下，之后不再改",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_player"
        verbose_name = "乙游玩家"
        verbose_name_plural = "乙游玩家"
        ordering = ["-id"]

    def __str__(self):
        return self.uid


class OtomePlayerGame(models.Model):
    """前端用户身上的游戏标签。进入某部游戏后自动打上。"""

    player = models.ForeignKey(OtomePlayer, on_delete=models.CASCADE, related_name="game_links", verbose_name="玩家")
    game = models.ForeignKey(OtomeGame, on_delete=models.CASCADE, related_name="player_links", verbose_name="游戏")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="打标时间")

    class Meta:
        db_table = "t_otome_player_game"
        verbose_name = "玩家游戏标签"
        verbose_name_plural = "玩家游戏标签"
        constraints = [
            models.UniqueConstraint(fields=["player", "game"], name="uniq_otome_player_game"),
        ]


class OtomeStaffGame(models.Model):
    """后台账号身上的游戏标签。"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="game_tags", verbose_name="后台用户")
    game = models.ForeignKey(OtomeGame, on_delete=models.CASCADE, related_name="staff_links", verbose_name="游戏")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="打标时间")

    class Meta:
        db_table = "t_otome_staff_game"
        verbose_name = "后台游戏标签"
        verbose_name_plural = "后台游戏标签"
        constraints = [
            models.UniqueConstraint(fields=["user", "game"], name="uniq_otome_staff_game"),
        ]


class OtomeSave(models.Model):
    """历史存档。每部游戏同时只保留一条自动存档，手动存档可以有多条。"""

    player = models.ForeignKey(OtomePlayer, on_delete=models.CASCADE, related_name="saves", verbose_name="玩家")
    game = models.ForeignKey(OtomeGame, on_delete=models.CASCADE, related_name="saves", verbose_name="游戏")
    node = models.ForeignKey(
        OtomeNode, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="saves", verbose_name="所在剧情",
    )
    node_key = models.CharField(max_length=64, blank=True, default="", verbose_name="剧情编号")
    title = models.CharField(max_length=100, blank=True, default="", verbose_name="标题")
    excerpt = models.CharField(max_length=200, blank=True, default="", verbose_name="摘要")
    is_auto = models.BooleanField(default=False, verbose_name="自动存档")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_save"
        verbose_name = "乙游存档"
        verbose_name_plural = "乙游存档"
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["player", "game"],
                condition=models.Q(is_auto=True),
                name="uniq_otome_autosave",
            )
        ]


class OtomeGalleryItem(models.Model):
    """故事解锁里的一条视频或立绘。"""

    KIND_VIDEO = "video"
    KIND_PORTRAIT = "portrait"
    KIND_CHOICES = (
        (KIND_VIDEO, "视频"),
        (KIND_PORTRAIT, "立绘"),
    )

    game = models.ForeignKey(OtomeGame, on_delete=models.CASCADE, related_name="gallery_items", verbose_name="所属游戏")
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, verbose_name="类型")
    asset = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gallery_items", verbose_name="素材",
    )
    title = models.CharField(max_length=100, verbose_name="标题")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    unlock_node = models.ForeignKey(
        OtomeNode, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gallery_unlocks", verbose_name="解锁剧情",
    )
    unlocked_by_default = models.BooleanField(default=False, verbose_name="默认解锁")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    is_insert = models.BooleanField(
        default=False, verbose_name="剧情插入",
        help_text="由剧情结束后的插入内容生成，看过或跳过后才解锁",
    )
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_gallery"
        verbose_name = "故事解锁"
        verbose_name_plural = "故事解锁"
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["game", "is_deleted", "sort_order", "id"], name="otome_gallery_game_alive"),
        ]


class OtomeUnlock(models.Model):
    player = models.ForeignKey(OtomePlayer, on_delete=models.CASCADE, related_name="unlocks", verbose_name="玩家")
    item = models.ForeignKey(OtomeGalleryItem, on_delete=models.CASCADE, related_name="unlocks", verbose_name="解锁内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="解锁时间")

    class Meta:
        db_table = "t_otome_unlock"
        verbose_name = "玩家解锁"
        verbose_name_plural = "玩家解锁"
        constraints = [
            models.UniqueConstraint(fields=["player", "item"], name="uniq_otome_unlock"),
        ]


class OtomeDataRecord(models.Model):
    """后台数据列表。每条都挂在一部游戏上，用来筛选。"""

    KIND_LOGIN = "login"
    KIND_SAVE = "save"
    KIND_UNLOCK = "unlock"
    KIND_PROGRESS = "progress"
    KIND_CHOICES = (
        (KIND_LOGIN, "登录"),
        (KIND_SAVE, "存档"),
        (KIND_UNLOCK, "解锁"),
        (KIND_PROGRESS, "进度"),
    )

    player = models.ForeignKey(OtomePlayer, on_delete=models.CASCADE, related_name="data_records", verbose_name="玩家")
    game = models.ForeignKey(OtomeGame, on_delete=models.CASCADE, related_name="data_records", verbose_name="游戏")
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, verbose_name="类型")
    title = models.CharField(max_length=120, blank=True, default="", verbose_name="标题")
    detail = models.CharField(max_length=300, blank=True, default="", verbose_name="说明")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="时间")

    class Meta:
        db_table = "t_otome_data"
        verbose_name = "乙游数据"
        verbose_name_plural = "乙游数据"
        ordering = ["-id"]


class OtomeAdChannel(models.Model):
    """用户来源。创建时生成渠道 ID，用来统计从这条广告进来的玩家。"""

    STATUS_OFF = 0
    STATUS_ON = 1
    STATUS_CHOICES = (
        (STATUS_OFF, "停用"),
        (STATUS_ON, "启用"),
    )

    channel_id = models.CharField(max_length=16, unique=True, verbose_name="渠道ID")
    name = models.CharField(max_length=100, verbose_name="来源名称")
    game = models.ForeignKey(
        OtomeGame, on_delete=models.CASCADE, related_name="ad_channels", verbose_name="对应游戏",
    )
    remark = models.CharField(max_length=200, blank=True, default="", verbose_name="备注")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    status = models.IntegerField(default=STATUS_ON, choices=STATUS_CHOICES, verbose_name="状态")
    visit_count = models.IntegerField(default=0, verbose_name="访问次数")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_ad_channel"
        verbose_name = "用户来源"
        verbose_name_plural = "用户来源"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.name} {self.channel_id}"


class OtomeAdClick(models.Model):
    """落地页上的一次访问。下载并打开游戏后，用这个标记把玩家对回来源。"""

    click_id = models.CharField(max_length=32, unique=True, verbose_name="访问标记")
    channel = models.ForeignKey(
        OtomeAdChannel, on_delete=models.CASCADE, related_name="clicks", verbose_name="来源",
    )
    ip = models.CharField(max_length=64, blank=True, default="", db_index=True, verbose_name="IP")
    user_agent = models.CharField(max_length=300, blank=True, default="", verbose_name="浏览器")
    platform = models.CharField(max_length=16, blank=True, default="", verbose_name="设备")
    device_id = models.CharField(max_length=128, blank=True, default="", db_index=True, verbose_name="设备号")
    player = models.ForeignKey(
        OtomePlayer, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ad_clicks", verbose_name="对上的玩家",
    )
    matched_at = models.DateTimeField(null=True, blank=True, verbose_name="对上时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="访问时间")

    class Meta:
        db_table = "t_otome_ad_click"
        verbose_name = "落地页访问"
        verbose_name_plural = "落地页访问"
        ordering = ["-id"]

    def __str__(self):
        return self.click_id


class OtomeBuiltinAd(models.Model):
    """游戏内展示的广告。每条只属于一部游戏。"""

    SLOT_LOADING = "loading"
    SLOT_BANNER = "banner"
    SLOT_POPUP = "popup"
    SLOT_CHOICES = (
        (SLOT_LOADING, "开场"),
        (SLOT_BANNER, "横幅"),
        (SLOT_POPUP, "弹窗"),
    )
    STATUS_OFF = 0
    STATUS_ON = 1
    STATUS_CHOICES = (
        (STATUS_OFF, "停用"),
        (STATUS_ON, "启用"),
    )

    game = models.ForeignKey(
        OtomeGame, on_delete=models.CASCADE, related_name="builtin_ads", verbose_name="对应游戏",
    )
    title = models.CharField(max_length=100, verbose_name="标题")
    texts = models.JSONField(default=dict, blank=True, verbose_name="多语言")
    slot = models.CharField(max_length=16, choices=SLOT_CHOICES, default=SLOT_LOADING, verbose_name="位置")
    image = models.ForeignKey(
        OtomeAsset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="builtin_ads", verbose_name="素材",
    )
    media_url = models.CharField(max_length=1000, blank=True, default="", verbose_name="外链素材")
    link_url = models.CharField(max_length=1000, blank=True, default="", verbose_name="点击地址")
    lang = models.CharField(max_length=16, default="zh-Hans", db_index=True, verbose_name="语言")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    status = models.IntegerField(default=STATUS_ON, choices=STATUS_CHOICES, verbose_name="状态")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "t_otome_builtin_ad"
        verbose_name = "内置广告"
        verbose_name_plural = "内置广告"
        ordering = ["sort_order", "-id"]

    def __str__(self):
        return self.title


class OtomeBuiltinAdEvent(models.Model):
    """一条内置广告被看到或点开。同一设备对同一条广告、同一种动作只记一次。"""

    ACTION_SHOW = "show"
    ACTION_CLICK = "click"
    ACTION_CHOICES = (
        (ACTION_SHOW, "展示"),
        (ACTION_CLICK, "点击"),
    )

    ad = models.ForeignKey(
        OtomeBuiltinAd, on_delete=models.CASCADE, related_name="events", verbose_name="广告",
    )
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name="动作")
    player = models.ForeignKey(
        "OtomePlayer", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="builtin_ad_events", verbose_name="玩家",
    )
    device_id = models.CharField(max_length=128, verbose_name="设备号")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="时间")

    class Meta:
        db_table = "t_otome_builtin_ad_event"
        verbose_name = "内置广告统计"
        verbose_name_plural = "内置广告统计"
        constraints = [
            models.UniqueConstraint(fields=["ad", "action", "device_id"], name="uniq_otome_builtin_ad_event"),
        ]

    def __str__(self):
        return f"{self.ad_id} {self.action}"
