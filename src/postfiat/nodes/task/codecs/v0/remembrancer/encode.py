from xrpl.wallet import Wallet

from postfiat.models.transaction import Transaction
from postfiat.nodes.task.codecs.v0.common import encode_account_msg as encode_common_msg
from postfiat.nodes.task.codecs.v0.serialization import encrypt_txn, compress_txn, chunk_txn
from postfiat.nodes.task.models.messages import Message, UserLogMessage, NodeLogResponseMessage, Direction

RESPONSE_SUFFIX = '_response'


def encode_account_msg(msg: Message, *, node_account: Wallet | str, user_account: Wallet | str) -> list[Transaction]:

    if not isinstance(node_account, Wallet) and msg.direction == Direction.NODE_TO_USER:
        raise ValueError('node_account must be a Wallet instance if message is direction USER_TO_NODE')
    if not isinstance(user_account, Wallet) and msg.direction == Direction.USER_TO_NODE:
        raise ValueError('user_account must be a Wallet instance if message is direction NODE_TO_USER')
    if not isinstance(msg, UserLogMessage | NodeLogResponseMessage):
        return []

    if isinstance(node_account, str) and not node_account.startswith('ED'):
        raise ValueError('node_account must be a valid public key or Wallet instance')
    if isinstance(user_account, str) and not user_account.startswith('ED'):
        raise ValueError('user_account must be a valid public key or Wallet instance')

    if txns := encode_common_msg(msg, node_account=node_account, user_account=user_account):
        return txns

    from_address = msg.user_wallet if msg.direction == Direction.USER_TO_NODE else msg.node_wallet
    to_address = msg.node_wallet if msg.direction == Direction.USER_TO_NODE else msg.user_wallet
    message_id = msg.message_id
    if msg.direction == Direction.NODE_TO_USER and not message_id.endswith(RESPONSE_SUFFIX):
        message_id = f'{message_id}{RESPONSE_SUFFIX}'

    txn = Transaction(
        from_address=from_address,
        to_address=to_address,
        amount_pft=msg.amount_pft,
        chunk_number=0,
        total_chunks=1,
        chunk_aggregation_key=message_id,
        memo_data=msg.message,
        memo_type=message_id,
        memo_format='',  # formerly used for discord id, not needed
    )

    node_pubkey = node_account.public_key if isinstance(node_account, Wallet) else node_account
    user_pubkey = user_account.public_key if isinstance(user_account, Wallet) else user_account
    pubkey = node_pubkey if msg.direction == Direction.USER_TO_NODE else user_pubkey
    secret = user_account.private_key if msg.direction == Direction.USER_TO_NODE else node_account.private_key
    txn = encrypt_txn(txn, pubkey, secret)
    txn = compress_txn(txn)
    txns = chunk_txn(txn)

    return txns

