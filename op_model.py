from datetime import datetime
from encode import get_user_op_hash
from typing import Dict
import json

def get_chainid(chain):
    with open('config.json') as json_file:
        data = json.load(json_file)
        return data.get(chain, {}).get('chainid', None)


class UserOp():
    def __init__(self, userop, entrypoint, chain, time):
        self.userop = userop
        self.entrypoint = entrypoint
        self.chain = chain
        self.time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
    def get_hash(self):
        return get_user_op_hash(self.userop, self.entrypoint, get_chainid(self.chain))

    def to_dict(self):
        return {
            'userop': self.userop,
            'entrypoint': self.entrypoint,
            'chain': self.chain,
            'time': self.time,
        }