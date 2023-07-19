from celery import Celery
import requests
import os
from database import Database
from op_model import UserOp
import json
from encode import get_user_op_hash
from celery.signals import task_prerun
from celery.utils.log import get_task_logger

app = Celery('schedule', broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'))


db = Database()

app.conf.update({
    'task_routes': {'tasks.add': {'queue': 'low-priority'}},
    'worker_hijack_root_logger': False,
})
app.log.setup_task_loggers()

logger = get_task_logger(__name__)

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    logger.info(f'Task {task_id} is about to run with args: {args} and kwargs: {kwargs}')

# 定义 Celery 任务
@app.task
def schedule_trade(data):
    try:
        logger.info('Starting schedule_trade task with data: %s', data)
        # Prepare Send Userop URL and headers
        logger.info('Preparing Send Userop URL and headers')
        url = f"{os.environ['BUNDLER_URL']}/" + data['chain']
        headers = {"Content-Type": "application/json"}

        # Prepare payload
        logger.info('Preparing payload')
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_sendUserOperation",
            "params": [data['userop'], data['entrypoint']]
        }

        # Send request and get response
        logger.info('Sending request to %s', url)
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        # Extract UserOperationHash from response
        logger.info('Extracting UserOperationHash from response')
        logger.info(response.json())
        user_op_hash = response.json()['result']

        # After operation is performed, update database
        logger.info('Updating database with completed status')
        db.update_scheduled_userop_status(user_op_hash, 'completed')

        logger.info('Preparing Trigger URL and headers')
        url = os.environ['TRIGGER_URL']
        headers = {"Content-Type": "application/json"}

        # Prepare payload
        logger.info('Preparing payload')
        payload = {
            "user_operation_hash": user_op_hash,
            "chain": data['chain']
        }

        # Send request and get response
        logger.info('Sending request to %s', url)
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        logger.info('Finished schedule_trade task')
        return user_op_hash

    except requests.exceptions.RequestException as e:
        logger.error('Error occurred: %s', e)
        logger.info('Updating database with failed status')
        db.update_scheduled_userop_status(get_user_op_hash(data['userop']), 'failed')
