FROM otome-base:v1

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
ENV DJANGO_SETTINGS_MODULE=uivsbe_backend.settings.pro
ENV PYTHONPATH=/app

WORKDIR /app

# 基础镜像里还没有 MinIO 客户端。只补这一个包，不重装全部依赖。
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ minio==7.2.15

COPY backend /app
# 挂载会盖住 /app/media，素材先放到挂载之外，启动时再写入宿主机的 media 目录。
RUN mkdir -p /opt/otome/seed-media \
    && if [ -d /app/media ]; then cp -a /app/media/. /opt/otome/seed-media/; fi
COPY deploy/entrypoint.sh /entrypoint.sh
COPY deploy/bootstrap.py /opt/otome/bootstrap.py
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]
