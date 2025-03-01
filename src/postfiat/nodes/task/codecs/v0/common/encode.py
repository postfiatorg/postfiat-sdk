from xrpl.wallet import Wallet

from postfiat.models.transaction import Transaction
from postfiat.nodes.task.models.messages import Message, Direction, NodeRefusalMessage


def encode_account_msg(msg: Message, *, node_account: Wallet | str, user_account: Wallet | str) -> list[Transaction]:

    if not isinstance(node_account, Wallet) and msg.direction == Direction.NODE_TO_USER:
        raise ValueError('node_account must be a Wallet instance if message is direction USER_TO_NODE')
    if not isinstance(user_account, Wallet) and msg.direction == Direction.USER_TO_NODE:
        raise ValueError('user_account must be a Wallet instance if message is direction NODE_TO_USER')

    if msg.direction == Direction.NODE_TO_USER:
        params = {
            'from_address': msg.node_wallet,
            'to_address': msg.user_wallet,
            'amount_pft': msg.amount_pft,
            'chunk_number': 0,
            'total_chunks': 1,
            'chunk_aggregation_key': None,
            'memo_data': '',
            'memo_type': '',
            'memo_format': '',
        }
        match msg:
            case NodeRefusalMessage():
                return [
                    Transaction(**params,
                                memo_type='REFUSAL REASON',
                                memo_data=msg.message),
                ]

    return []