from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tasks import schedule_trade
from database import get_scheduled_userop_by_userophash, get_all_scheduled_userops as get_all, update_scheduled_userop_status, create_scheduled_userop
import os
import json
from datetime import datetime
import logging

# 创建日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

app = FastAPI()

# 自定义装饰器，用于记录日志和处理异常
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        logger.info(f"Entering {func.__name__}")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal Server Error")
        finally:
            logger.info(f"Exiting {func.__name__}")
    return wrapper

# 定义数据模型
class UserOp(BaseModel):
    userop: str
    entrypoint: str
    chain: str
    time: datetime

# 调度交易
@app.post('/schedule')
@handle_exceptions
def schedule_view(userop: UserOp):
    scheduled_userop = get_scheduled_userop_by_userophash(userop.userop)
    if scheduled_userop:
        raise HTTPException(status_code=400, detail="Trade already scheduled")

    create_scheduled_userop(userop.userop, 'Scheduled')

    result = schedule_trade.apply_async(args=[userop.dump()], eta=userop.time)

    update_scheduled_userop_status(userop.userop, result.id)

    logger.info(f"Trade scheduled with ID {result.id}")
    return {'message': f'Trade scheduled with ID {result.id}', 'userop': userop.dump()}

# 取消调度的交易
@app.post('/cancel')
@handle_exceptions
def cancel_schedule_view(userop: str):
    scheduled_userop = get_scheduled_userop_by_userophash(userop)
    if scheduled_userop:
        task_id = scheduled_userop['task_id']
        schedule_trade.AsyncResult(task_id).revoke(terminate=True)

        update_scheduled_userop_status(userop, 'Cancelled')

        logger.info(f"Trade cancelled: {userop}")
        return {'message': 'Trade cancelled', 'userop': userop}
    else:
        raise HTTPException(status_code=404, detail="Trade not found")

# 获取所有调度的交易
@app.get('/scheduled_userops')
@handle_exceptions
def get_all_scheduled_userops():
    scheduled_userops = get_all()
    return scheduled_userops
