import redis

# 连接 WSL 中的 Redis
r = redis.Redis(
    host='127.0.0.1',  # WSL 的 IP 地址
    port=6379,            # 映射的端口（6379 或 6380）
    password='your_redis_password',
    decode_responses=True
)

# 测试连接
r.set('test', 'hello from Windows')
print(r.get('test'))