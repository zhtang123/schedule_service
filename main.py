import time

from fastapi import FastAPI, HTTPException, Request  # 导入 Request
from tasks import schedule_trade
from database import Database
from threading import Thread
import os
import json
from datetime import datetime
import uvicorn
from datetime import datetime
from encode import get_user_op_hash
from op_model import UserOp
import logging

# 创建日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

db = Database()

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

# 调度交易
@app.post('/schedule')

async def schedule_view(request: Request):
    print("FU")
    body = await request.body()
    data = json.loads(body)
    userop = UserOp(data['userop'], data['entrypoint'], data['chain'], data['time'])
    userophash = userop.get_hash()
    scheduled_userop = db.get_scheduled_userop(userophash)

    if scheduled_userop:
        raise HTTPException(status_code=400, detail="Trade already scheduled")

    result = schedule_trade.apply_async(args=[userop.to_dict()], eta=userop.time)

    db.insert_scheduled_userop(userophash, 'scheduled', result.id, userop.time)

    logger.info(f"Trade scheduled with ID {result.id}")
    return {'message': f'Trade scheduled with ID {result.id}', 'userophash': userophash}


@app.post('/scheduled_userop')
@handle_exceptions
async def get_scheduled_userop(request: Request):
    data = await request.json()
    userophash = data.get('userophash', None)

    if not userophash:
        raise HTTPException(status_code=400, detail="Missing userophash parameter")

    scheduled_userop = db.get_scheduled_userop(userophash)

    if scheduled_userop:
        logger.info(f"Retrieved trade: {userophash}")
        return scheduled_userop
    else:
        raise HTTPException(status_code=404, detail="Trade not found")


# 取消调度的交易
@app.post('/cancel')
@handle_exceptions
def cancel_schedule_view(userophash: str):
    scheduled_userop = db.get_scheduled_userop(userophash)

    if scheduled_userop:
        task_id = scheduled_userop['task_id']
        schedule_trade.AsyncResult(task_id).revoke(terminate=True)

        db.update_scheduled_userop_status(userophash, 'cancelled')

        logger.info(f"Trade cancelled: {userophash}")
        return {'message': 'Trade cancelled', 'userophash': userophash}
    else:
        raise HTTPException(status_code=404, detail="Trade not found")

# 获取所有调度的交易
@app.get('/scheduled_userops')
@handle_exceptions
def get_all_scheduled_userops():
    scheduled_userops = db.get_all_scheduled_userops()
    return scheduled_userops

def worker():
    logger.warning(datetime.now())
    time.sleep(1)

if __name__ == "__main__":
    worker = Thread(target=worker)
    worker.start()
    uvicorn.run(app, host="0.0.0.0", port=12010)
