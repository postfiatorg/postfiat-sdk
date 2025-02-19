import re

from postfiat.models.transaction import Transaction, UNKNOWN_TOTAL_CHUNKS
from postfiat.nodes.task.codecs.v0.errors import DecodingError

RE_CHUNK_PREFIX = re.compile(r'chunk_\d+__(?P<payload>.*)')
CHUNK_SIZE = 900


def dechunk_memos(memos: list[str]) -> str:
    recombined_payload: list[str] = []
    for memo in memos:
        if (m := RE_CHUNK_PREFIX.match(memo)):
            recombined_payload.append(m.group('payload'))
        else:
            raise DecodingError(f'invalid chunk: {memo}')
    return ''.join(recombined_payload)


def chunk_memo(memo: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    chunks = (memo[i:i+chunk_size] for i in range(0, len(memo), chunk_size))
    return [f'chunk_{i+1}__{chunk}' for i, chunk in enumerate(chunks)]


def dechunk_txns(txns: list[Transaction]) -> Transaction:
    # validate chunked message consistency
    if txns[0].total_chunks != UNKNOWN_TOTAL_CHUNKS and len(txns) != txns[0].total_chunks:
        raise DecodingError(f'expected {txns[0].total_chunks} chunks, got {len(txns)}')
    
    for i, txn in enumerate(txns):
        if (txn.chunk_aggregation_key != txns[0].chunk_aggregation_key or
            txn.total_chunks != txns[0].total_chunks or
            txn.chunk_number != i
        ):
            raise DecodingError(f'inconsistent chunking params: {txn} vs {txns[0]}')
    
    # recombine chunks into single payload and transaction
    return txns[0].model_copy(update={
        'chunk_number': 0,
        'total_chunks': 1,
        'amount_pft': sum(txn.amount_pft for txn in txns),
        'memo_data': dechunk_memos([txn.memo_data for txn in txns]),
    })


def chunk_txn(txn: Transaction) -> list[Transaction]:
    chunks = chunk_memo(txn.memo_data)
    txns = []
    for i, chunk in enumerate(chunks):
        txns.append(txn.model_copy(update={
            'chunk_number': i,
            'total_chunks': len(chunks),
            'amount_pft': txn.amount_pft / len(chunks),
            'chunk_aggregation_key': txn.memo_type,
            'memo_data': chunk,
        }))
    return txns