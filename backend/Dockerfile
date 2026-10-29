FROM python:3.11-slim

# 环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 配置国内pip源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --upgrade pip

# 核心：替换为Debian Trixie兼容的OpenCV依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 原有PostgreSQL依赖
    postgresql-client \
    build-essential \
    libpq-dev \
    # 兼容版OpenCV依赖（替换libgl1-mesa-glx为libgl1）
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/*

# 工作目录+安装Python依赖+复制代码（原有逻辑不变）
WORKDIR /app
COPY req.txt .
RUN pip install --no-cache-dir -r req.txt
COPY . .

# 暴露端口（仅容器内，无宿主机映射）
EXPOSE 8000

# 创建静态文件目录（与docker-compose中的staticfiles卷匹配）
RUN mkdir -p /app/staticfiles && \
    chmod -R 755 /app/staticfiles  # 授权避免Nginx读不到

