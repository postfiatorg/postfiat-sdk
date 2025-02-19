import base64
import brotli

from postfiat.models.transaction import Transaction

PREFIX = 'COMPRESSED__'


def compress_memo(memo: str) -> str:
    data = brotli.compress(memo.encode('utf-8'))
    return f'{PREFIX}{base64.b64encode(data).decode("utf-8")}'


def decompress_memo(data: str) -> str:
    assert data.startswith(PREFIX), f'invalid memo prefix: {data}'
    data = data[len(PREFIX):]
    data = base64.b64decode(data.encode('utf-8'))
    data = brotli.decompress(data).decode('utf-8')
    return data


def compress_txn(txn: Transaction) -> Transaction:
    memo_data = compress_memo(txn.memo_data)
    return txn.model_copy(update={'memo_data': memo_data})


def decompress_txn(txn: Transaction) -> Transaction:
    memo_data = decompress_memo(txn.memo_data)
    return txn.model_copy(update={'memo_data': memo_data})
