from datetime import datetime
from decimal import Decimal
import json
import re
from typing import Any, Self

from pydantic import BaseModel
from xrpl.utils import hex_to_str, str_to_hex

from postfiat.nodes.task.constants import TOKEN, TOKEN_ISSUER

REGEX_LEGACY_CHUNK_NUMBER = re.compile(r'^chunk_(\d+)__')

UNKNOWN_TOTAL_CHUNKS = object()


# TODO distinguish inbound and outbound transactions?
class Transaction(BaseModel):
    data: dict | None = None
    chunk_number: int
    total_chunks: int | Any
    chunk_aggregation_key: str | None
    ledger_index: int | None = None
    transaction_index: int | None = None
    timestamp: datetime | None = None
    from_pubkey: str | None = None
    from_address: str
    to_address: str = ''
    hash: str | None = None
    memo_data: str = ''
    memo_format: str = ''
    memo_type: str = ''
    amount_pft: Decimal = 0

    def __lt__(self, other: Self) -> bool:
        return (self.ledger_index, self.transaction_index) < (other.ledger_index, other.transaction_index)

    @classmethod
    def from_raw_json(cls, raw_json: str) -> Self:
        return cls.from_dict(json.loads(raw_json))

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        memo_data = ''
        memo_format = ''
        memo_type = ''
        if ('Memos' in data['tx_json'] and 
            len(data['tx_json']['Memos']) > 0 and
            'Memo' in data['tx_json']['Memos'][0]
        ):
            memo = data['tx_json']['Memos'][0]['Memo']
            memo_data = hex_to_str(memo.get('MemoData', ''))
            memo_format = hex_to_str(memo.get('MemoFormat', ''))
            memo_type = hex_to_str(memo.get('MemoType', ''))

        chunk_number = 0
        total_chunks = 1
        chunk_aggregation_key = None
        if memo_data and (m := REGEX_LEGACY_CHUNK_NUMBER.match(memo_data)):
            chunk_number = int(m.group(1)) - 1
            total_chunks = UNKNOWN_TOTAL_CHUNKS
            chunk_aggregation_key = memo_type
        return cls(
            data=data,
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            chunk_aggregation_key=chunk_aggregation_key,
            ledger_index=int(data['ledger_index']),
            transaction_index=int(data['meta']['TransactionIndex']),
            timestamp=datetime.fromisoformat(data['close_time_iso']),
            from_pubkey=data['tx_json']['SigningPubKey'],
            from_address=data['tx_json']['Account'],
            to_address=data['tx_json']['Destination'] if 'Destination' in data['tx_json'] else '',
            hash=data['hash'],
            memo_data=memo_data,
            memo_format=memo_format,
            memo_type=memo_type,
            amount_pft=Decimal(
                data['meta']['delivered_amount'].get('value', 0)
                if (
                    'delivered_amount' in data['meta'] and
                    isinstance(data['meta']['delivered_amount'], dict) and
                    data['meta']['delivered_amount'].get('currency', TOKEN) == TOKEN and
                    data['meta']['delivered_amount'].get('issuer', TOKEN_ISSUER) == TOKEN_ISSUER
                ) else 0
            ),
        )

    def to_raw_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self) -> dict:
        if self.data is not None:
            return self.data
        return {
            'account': self.from_address,
            'transaction_type': 'Payment',
            'memos': [{
                'memo': {
                    'memo_data': str_to_hex(self.memo_data),
                    'memo_format': str_to_hex(self.memo_format),
                    'memo_type': str_to_hex(self.memo_type),
                }
            }],
            'amount': {
                'currency': TOKEN,
                'issuer': TOKEN_ISSUER,
                'value': str(self.amount_pft),
            },
            'destination': self.to_address,
        }
