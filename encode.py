from web3 import Web3
from eth_abi import encode


def get_user_op_hash(op, entry_point, chain_id):
    hash_init_code = Web3.keccak(hexstr=op['initCode'])
    hash_call_data = Web3.keccak(hexstr=op['callData'])
    hash_paymaster_and_data = Web3.keccak(hexstr=op['paymasterAndData'])

    pack = encode(
        ["address", "uint256", "bytes32", "bytes32", "uint256", "uint256", "uint256", "uint256", "uint256", "bytes32"],
        [
            op['sender'],
            int(op['nonce'], 16),
            bytes(hash_init_code),
            bytes(hash_call_data),
            int(op['callGasLimit'], 16),
            int(op['verificationGasLimit'], 16),
            int(op['preVerificationGas'], 16),
            int(op['maxFeePerGas'], 16),
            int(op['maxPriorityFeePerGas'], 16),
            bytes(hash_paymaster_and_data),
        ]
    )

    packhash = Web3.keccak(hexstr=pack.hex())

    tmp = str(Web3.keccak(encode(["bytes32", "address", "uint256"], [packhash, entry_point, chain_id])).hex())

    return tmp
