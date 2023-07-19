import os

# 使用 Redis 作为消息中间人，确保将以下信息替换为实际的 Redis 连接信息
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')

# 使用 Redis 作为结果后端，确保将以下信息替换为实际的 Redis 连接信息
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# 使用 JSON 作为任务序列化器
task_serializer = 'json'

# 使用 JSON 作为结果序列化器
result_serializer = 'json'

# 接受 JSON 内容
accept_content = ['json']

# 设置时区，假设您的时区是 'Asia/Shanghai'
timezone = 'Asia/Shanghai'

# 启用 UTC
enable_utc = True

# 默认的队列、交换、路由键、交付模式、优先级
task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'
task_default_delivery_mode = 'persistent'
