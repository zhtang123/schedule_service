from eth_hash.auto import keccak
from eth_abi import encode


def get_user_op_hash(op, entry_point, chain_id):
    hash_init_code = keccak(op['initCode'])
    hash_call_data = keccak(op['callData'])
    hash_paymaster_and_data = keccak(op['paymasterAndData'])

    pack = encode(
        ["address", "uint256", "bytes32", "bytes32", "uint256", "uint256", "uint256", "uint256", "uint256", "bytes32"],
        [
            op['sender'],
            op['nonce'],
            hash_init_code,
            hash_call_data,
            op['callGasLimit'],
            op['verificationGasLimit'],
            op['preVerificationGas'],
            op['maxFeePerGas'],
            op['maxPriorityFeePerGas'],
            hash_paymaster_and_data,
        ]
    )

    hash_pack = keccak(pack)

    return keccak(encode(["bytes32", "address", "uint256"], [hash_pack, entry_point, chain_id]))
