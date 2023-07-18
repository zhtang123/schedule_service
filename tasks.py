
from celery import Celery
import os

# 创建 Celery 应用
app = Celery('schedule', broker='pyamqp://guest@localhost//')

# 定义 Celery 任务
@app.task
def schedule_trade(data):
    # 执行操作
    # 准备请求的 URL 和头部信息
    url = f"http://{os.environ['BUNDLER_URL']}/bundler/" + data['chain']
    headers = {"Content-Type": "application/json"}

    # 准备请求的载荷
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_sendUserOperation",
        "params": [data['userop'], data['entrypoint']]
    }

    # 发送请求并获取响应
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # 从响应中提取 UserOperationHash
    user_op_hash = response.json()['result']

    user_op = data['userop']
    entrypoint = data['entrypoint']
    chain = data['chain']
    time = data['time']

    user_op_hash = get_user_op_hash(user_op, entrypoint, chain)

    # 操作执行后，更新数据库
    update_scheduled_userop_status(user_op_hash, 'completed')

    return user_op_hash
