import os
import math
import requests
import logging
import json
from celery import Celery
from database import Database
from op_model import get_chainid
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

def fetch_gas_prices(chain_id):
    logger.info('Fetching gas prices for chain id: %s', chain_id)
    url = f"https://gas-api.metaswap.codefi.network/networks/{chain_id}/suggestedGasFees"
    response = requests.get(url)
    data = response.json()

    logger.info(f"here gas response {data}")

    suggested_max_fee_per_gas = hex(math.ceil(float(data["high"]["suggestedMaxFeePerGas"]) * 1000))
    suggested_max_priority_fee_per_gas = hex(math.ceil(float(data["high"]["suggestedMaxPriorityFeePerGas"]) * 1000))

    logger.info('Fetched and converted gas prices: MaxFeePerGas = %s, MaxPriorityFeePerGas = %s',
                suggested_max_fee_per_gas, suggested_max_priority_fee_per_gas)

    return suggested_max_fee_per_gas, suggested_max_priority_fee_per_gas

def update_gas_prices_in_userop(data, suggested_max_fee_per_gas, suggested_max_priority_fee_per_gas, chainid):
    logger.info('Updating gas prices in user operation')
    old_userop_hash = get_user_op_hash(data['userop'], data['entrypoint'], chainid)

    # Update userop with suggested gas prices
    data['userop']['maxFeePerGas'] = suggested_max_fee_per_gas
    data['userop']['maxPriorityFeePerGas'] = suggested_max_priority_fee_per_gas

    new_userop_hash = get_user_op_hash(data['userop'], data['entrypoint'], chainid)

    logger.info(f"old_hash:{old_userop_hash}, new_hash{new_userop_hash}")

    if old_userop_hash != new_userop_hash:
        db.update_modified_userop(old_userop_hash, new_userop_hash)

    return data

def send_user_operation(data):
    logger.info('Sending user operation')
    url = os.path.join(os.environ['BUNDLER_URL'], data['chain'])
    headers = {"Content-Type": "application/json"}

    # Prepare payload
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_sendUserOperation",
        "params": [data['userop'], data['entrypoint']]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()

    try:
        # Extract UserOperationHash from response
        user_op_hash = response.json()['result']

    except Exception as e:
        logger.error(response.json())
        db.update_scheduled_userop_status(get_user_op_hash(data['userop'], data['entrypoint'], chainid), 'failed')
        raise e

    logger.info('Received UserOperationHash %s', user_op_hash)

    # After operation is performed, update database
    db.update_scheduled_userop_status(user_op_hash, 'completed')

    return user_op_hash

def trigger_next_operation(data, user_op_hash):
    logger.info('Triggering the next operation')
    url = os.environ['TRIGGER_URL']
    headers = {"Content-Type": "application/json"}

    # Prepare payload
    payload = {
        "user_operation_hash": user_op_hash,
        "chain": data['chain']
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

@app.task
def schedule_trade(data):
    logger.info('Starting schedule_trade task with data: %s', data)
    chainid = get_chainid(data['chain'])

    try:
        # Fetch suggested gas prices
        suggested_max_fee_per_gas, suggested_max_priority_fee_per_gas = fetch_gas_prices(chainid)

        # Update userop with suggested gas prices
        data = update_gas_prices_in_userop(data, suggested_max_fee_per_gas, suggested_max_priority_fee_per_gas, chainid)

        # Send User Operation
        user_op_hash = send_user_operation(data)

        # Trigger the next operation
        trigger_next_operation(data, user_op_hash)

        logger.info('Finished schedule_trade task')
        return user_op_hash

    except requests.exceptions.RequestException as e:
        logger.error('Request error occurred: %s', e)
        db.update_scheduled_userop_status(get_user_op_hash(data['userop'], data['entrypoint'], chainid), 'failed')
