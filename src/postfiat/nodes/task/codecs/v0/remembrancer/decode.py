from collections import defaultdict
import operator
import os
from typing import AsyncIterator
import logging

from xrpl.wallet import Wallet

from postfiat.models.transaction import Transaction, UNKNOWN_TOTAL_CHUNKS
from postfiat.nodes.task.codecs.v0.errors import DecodingError
from postfiat.nodes.task.codecs.v0.serialization import dechunk_txns, decompress_txn, decrypt_txn, is_txn_encrypted
from postfiat.nodes.task.models.messages import Message, UserLogMessage, NodeLogResponseMessage, NodeRefusalMessage

log = logging.getLogger(__name__)

MAX_CHUNKS = 20

RESPONSE_SUFFIX = '_response'

# shared cache of pubkeys for memo decryption
# should be relatively safe to use module cache since
# each address only has one possible pubkey
__pubkey_cache: dict[str, str] = {}


def __set_key(address: str, pubkey: str):
    __pubkey_cache[address] = pubkey


def __get_key(txn: Transaction, our_address: str) -> str:
    if txn.from_address == our_address:
        other_address = txn.to_address
    else:
        other_address = txn.from_address
    return __pubkey_cache[other_address]

    
def __maybe_decrypt_txn(txn: Transaction, our_wallet: Wallet | None) -> Transaction:
    if is_txn_encrypted(txn) and our_wallet:
        pubkey = __get_key(txn, our_wallet.address)
        txn = decrypt_txn(txn, pubkey, our_wallet.private_key)
    return txn


def _filter(txn: Transaction, *, node_account: Wallet | str, user_account: Wallet | None) -> bool:
    if isinstance(node_account, Wallet):
        node_account = node_account.address
    if isinstance(user_account, Wallet):
        user_account = user_account.address
    try:
        return (
            txn.data['validated'] and
            txn.data['meta']['TransactionResult'] == 'tesSUCCESS' and
            txn.data['tx_json']['TransactionType'] == 'Payment' and
            node_account in [txn.to_address, txn.from_address] and
            (user_account is None or user_account in [txn.to_address, txn.from_address]) and
            txn.memo_data and
            txn.memo_type
        )
    except (KeyError, TypeError, IndexError, AttributeError) as e:
        log.debug(f'error filtering txn: {e}')
        return False


def _build(txns: list[Transaction], *, node_account: Wallet | str, user_account: Wallet | None) -> Message:
    if len(txns) == 0:
        raise ValueError('no txns to decode')

    txn = dechunk_txns(txns)
    txn = decompress_txn(txn)

    our_wallet = None
    if isinstance(node_account, Wallet):
        our_wallet = node_account
    elif isinstance(user_account, Wallet):
        our_wallet = user_account
    txn = __maybe_decrypt_txn(txn, our_wallet)

    txn_properties = {
        'amount_pft': txn.amount_pft,
        'timestamp': txn.timestamp,
        'hash': txn.hash,
        'raw_data': txn.memo_data,
        'ledger_seq': txn.ledger_index,
        'transaction_seq': txn.transaction_index,
    }
    node_address = node_account if isinstance(node_account, str) else node_account.address
    if txn.to_address == node_address: # user to node
        txn_properties['user_wallet'] = txn.from_address
        txn_properties['user_pubkey'] = txn.from_pubkey
        txn_properties['node_wallet'] = txn.to_address
        return UserLogMessage(
            **txn_properties,
            message_id=txn.memo_type,
            message=txn.memo_data,
        )
    elif txn.from_address == node_address: # node to user
        txn_properties['user_wallet'] = txn.to_address
        txn_properties['node_wallet'] = txn.from_address
        txn_properties['node_pubkey'] = txn.from_pubkey

        if txn.memo_type == 'REFUSAL REASON':
            return NodeRefusalMessage(
                **txn_properties,
                message=txn.memo_data,
            )

        message_id = txn.memo_type
        if message_id.endswith(RESPONSE_SUFFIX):
            message_id = message_id[:-len(RESPONSE_SUFFIX)]
        return NodeLogResponseMessage(
            **txn_properties,
            message_id=message_id,
            message=txn.memo_data,
        )
    else:
        raise ValueError(f'unknown txn direction: {txn}')


def decode_account_txn(txns: Transaction | list[Transaction], *, node_account: Wallet | str, user_account: Wallet | None = None) -> Message | None:
    msg = None
    if isinstance(txns, Transaction):
        txns = [txns]
    __set_key(txns[0].from_address, txns[0].from_pubkey)
    try:
        txns = [txn for txn in txns if _filter(txn, node_account=node_account, user_account=user_account)]
    except DecodingError:
        return None
    try:
        msg = _build(txns, node_account=node_account, user_account=user_account)
    except Exception as e:
        log.debug(f'error building message: {e}')
    return msg


async def decode_account_stream(txns: AsyncIterator[Transaction], *, node_account: Wallet | str, user_account: Wallet | None = None) -> AsyncIterator[Message]:
    txn_buffer = defaultdict(list)
    async for txn in txns:
        try:
            if txn.total_chunks == 1:
                if msg := decode_account_txn(txn, node_account=node_account, user_account=user_account):
                    yield msg
            elif isinstance(txn.total_chunks, int) and txn.total_chunks > MAX_CHUNKS:
                log.debug(f'skipping txn with too many chunks: {txn.total_chunks} (limit: {MAX_CHUNKS})')
            elif txn.chunk_aggregation_key:
                buf = txn_buffer[txn.chunk_aggregation_key]
                buf.append(txn)
                buf.sort(key=operator.attrgetter('chunk_number'))
                if len(buf) > MAX_CHUNKS:
                    # we have too many chunks, drop all of them
                    log.debug(f'too many chunks for txn {txn.chunk_aggregation_key}: {len(buf)} (limit: {MAX_CHUNKS}), dropping all chunks')
                    del txn_buffer[txn.chunk_aggregation_key]
                elif len(buf) == txn.total_chunks:
                    # we have all expected chunks
                    try:
                        if msg := decode_account_txn(buf, node_account=node_account, user_account=user_account):
                            yield msg
                    except DecodingError:
                        raise
                    finally:
                        del txn_buffer[txn.chunk_aggregation_key]
                elif txn.total_chunks == UNKNOWN_TOTAL_CHUNKS:
                    # we don't know if we have all chunks, try it
                    if msg := decode_account_txn(buf, node_account=node_account, user_account=user_account):
                        del txn_buffer[txn.chunk_aggregation_key]
                        yield msg
            else:
                log.debug(f'inconsistent chunking params: {txn}')
        except Exception as e:
            if txn.total_chunks == 1:
                log.debug(f'error decoding txn: {e} -- raw txn:{os.linesep}{txn}')
