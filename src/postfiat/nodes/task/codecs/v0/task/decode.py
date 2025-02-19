from decimal import Decimal
import os
import re
from typing import AsyncIterator

from xrpl.wallet import Wallet

from postfiat.models.transaction import Transaction
from postfiat.nodes.task.codecs.v0.serialization import is_txn_encrypted, decrypt_txn
from postfiat.nodes.task.models.messages import (
    Message,
    UserHandshakeMessage, UserGDocContextMessage, UserInitiationRiteMessage,
    UserSweepAddressMessage, UserRequestMessage, UserAcceptanceMessage,
    UserRefusalMessage, UserCompletionMessage, UserChallengeResponseMessage,
    NodeHandshakeMessage, NodeWalletFundingMessage,
    NodeInitiationRewardMessage, NodeProposalMessage, NodeChallengeMessage,
    NodeRewardMessage, NodeBlacklistMessage,
)

REGEX_TASK_ID = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}:\d{2}__[A-Z]{2}[0-9]{2}')
REGEX_TASK_DATA = re.compile(r'([A-Z _]*[A-Z]) ___? ?([\S\s]*)$')
REGEX_PROPOSED_TASK_DATA = re.compile(r'([\S\s]*) \.\. (\d+)$')

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


class DecodingError(Exception):
    pass

class AccountTypeLabels:
    HANDSHAKE = 'HANDSHAKE'
    GDOC_CONTEXT_LINK = 'google_doc_context_link'
    INITIATION_RITE = 'INITIATION_RITE'
    WALLET_FUNDING = 'discord_wallet_funding'
    INITIATION_REWARD = 'INITIATION_REWARD'
    SWEEP_ADDRESS = 'SWEEP WALLET'
    BLACKLIST = 'BLACKLIST'

class TaskTypeLabels:
    REQUEST = 'REQUEST_POST_FIAT'
    PROPOSED = 'PROPOSED PF'
    ACCEPTANCE = 'ACCEPTANCE REASON'
    REFUSAL = 'REFUSAL REASON'
    COMPLETION = 'COMPLETION JUSTIFICATION'
    CHALLENGE = 'VERIFICATION PROMPT'
    RESPONSE = 'VERIFICATION RESPONSE'
    REWARD = 'REWARD RESPONSE'

# TODO: is this really necessary or valuable to do given Transaction-level validation?
# TODO: make filtering more specific to the message type / task node usecase
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
            txn.memo_format and
            txn.memo_type
        )
    except (KeyError, TypeError, IndexError, AttributeError) as e:
        print(f'error filtering txn: {e}')
        return False

def _build(txns: list[Transaction], *, node_account: Wallet | str, user_account: Wallet | None) -> Message:
    if len(txns) > 1:
        raise DecodingError('no chunking support yet')
    elif len(txns) == 0:
        raise DecodingError('no transactions to decode')

    # no chunking support for task txns yet
    # no compression support for task txns yet
    txn = txns[0]

    our_wallet = None
    if isinstance(node_account, Wallet):
        our_wallet = node_account
    elif isinstance(user_account, Wallet):
        our_wallet = user_account
    txn = __maybe_decrypt_txn(txn, our_wallet)

    if isinstance(node_account, Wallet):
        node_account = node_account.address
    if isinstance(user_account, Wallet):
        user_account = user_account.address

    txn_properties = {
        'amount_pft': txn.amount_pft,
        'timestamp': txn.timestamp,
        'hash': txn.hash,
        'raw_data': txn.memo_data,
        'ledger_seq': txn.ledger_index,
        'transaction_seq': txn.transaction_index,
    }
    
    if txn.to_address == node_account: # user to node
        txn_properties['user_wallet'] = txn.from_address
        txn_properties['node_wallet'] = txn.to_address
        match txn.memo_type:
            case AccountTypeLabels.HANDSHAKE:
                return UserHandshakeMessage(
                    **txn_properties,
                    pubkey=txn.memo_data,
                )
            case AccountTypeLabels.GDOC_CONTEXT_LINK:
                return UserGDocContextMessage(
                    **txn_properties,
                    pubkey=txn.from_pubkey,
                    gdoc_context_link=txn.memo_data,
                )
            case AccountTypeLabels.INITIATION_RITE:
                return UserInitiationRiteMessage(
                    **txn_properties,
                    message=txn.memo_data,
                )
            case AccountTypeLabels.SWEEP_ADDRESS:
                return UserSweepAddressMessage(
                    **txn_properties,
                    sweep_address=txn.memo_data,
                )
        if REGEX_TASK_ID.fullmatch(txn.memo_type) and (
            m := REGEX_TASK_DATA.fullmatch(txn.memo_data)
        ):
            task_message_type, task_data = m.groups()
            txn_properties['task_id'] = txn.memo_type
            match task_message_type:
                case TaskTypeLabels.REQUEST:
                    return UserRequestMessage(
                        **txn_properties,
                        message=task_data,
                    )
                case TaskTypeLabels.ACCEPTANCE:
                    return UserAcceptanceMessage(
                        **txn_properties,
                        message=task_data,
                    )
                case TaskTypeLabels.REFUSAL:
                    return UserRefusalMessage(
                        **txn_properties,
                        message=task_data,
                    )
                case TaskTypeLabels.COMPLETION:
                    return UserCompletionMessage(
                        **txn_properties,
                        message=task_data,
                    )
                case TaskTypeLabels.RESPONSE:
                    return UserChallengeResponseMessage(
                        **txn_properties,
                        message=task_data,
                    )
                case _:
                    raise ValueError(f'invalid task message type: "{task_message_type}"')
        else:
            raise ValueError(f'unknown task message type: "{txn.memo_type}" or invalid task data: "{txn.memo_data}"')

    elif txn.from_address == node_account: # node to user
        txn_properties['user_wallet'] = txn.to_address
        txn_properties['node_wallet'] = txn.from_address
        match txn.memo_type:
            case AccountTypeLabels.HANDSHAKE:
                return NodeHandshakeMessage(
                    **txn_properties,
                    pubkey=txn.memo_data,
                )
            case AccountTypeLabels.WALLET_FUNDING:
                return NodeWalletFundingMessage(
                    **txn_properties,
                )
            case AccountTypeLabels.INITIATION_REWARD:
                return NodeInitiationRewardMessage(
                    **txn_properties,
                    message=txn.memo_data,
                )
            case AccountTypeLabels.BLACKLIST:
                return NodeBlacklistMessage(
                    **txn_properties,
                )
        if REGEX_TASK_ID.fullmatch(txn.memo_type) and (
            m := REGEX_TASK_DATA.fullmatch(txn.memo_data)
        ):
            task_message_type, task_data = m.groups()
            txn_properties['task_id'] = txn.memo_type
            match task_message_type:
                case TaskTypeLabels.PROPOSED:
                    m = REGEX_PROPOSED_TASK_DATA.fullmatch(task_data)
                    task_data, pft_offer = m.groups()
                    return NodeProposalMessage(
                        **txn_properties,
                        message=task_data,
                        pft_offer=Decimal(pft_offer),
                    )
                case TaskTypeLabels.CHALLENGE:
                    return NodeChallengeMessage(
                        **txn_properties,
                        message=task_data,
                    )
                case TaskTypeLabels.REWARD:
                    return NodeRewardMessage(
                        **txn_properties,
                        message=task_data,
                    )

        # Support legacy task proposal message with no prefix
        elif m := REGEX_PROPOSED_TASK_DATA.fullmatch(txn.memo_data):
            task_data, pft_offer = m.groups()
            txn_properties['task_id'] = txn.memo_type
            return NodeProposalMessage(
                **txn_properties,
                message=task_data,
                pft_offer=Decimal(pft_offer),
            )

        else:
            raise ValueError(f'unknown task message type: "{txn.memo_type}" or invalid task data: "{txn.memo_data}"')
    else:
        raise ValueError(f'neither from:"{txn.from_address}" nor to:"{txn.to_address}" is {node_account}')

def decode_account_txn(txns: Transaction | list[Transaction], *, node_account: Wallet | str, user_account: Wallet | None = None) -> Message | None:
    msg = None
    if isinstance(txns, Transaction):
        txns = [txns]
    __set_key(txns[0].from_address, txns[0].from_pubkey)
    try:
        txns = [txn for txn in txns if _filter(txn, node_account=node_account, user_account=user_account)]
    except DecodingError:
        return None
    assert len(txns) <= 1, 'chunking not supported yet'
    try:
        msg = _build(txns, node_account=node_account, user_account=user_account)
    except Exception as e:
        print(f'error building message: {e}')
        raise
    return msg

async def decode_account_stream(txns: AsyncIterator[Transaction], *, node_account: Wallet | str, user_account: Wallet | None = None) -> AsyncIterator[Message]:
    # TODO: chunk support if needed: buffer message chunks and aggregate chunks by message
    async for txn in txns:
        try:
            if msg := decode_account_txn(txn, node_account=node_account, user_account=user_account):
                yield msg
        except Exception as e:
            print(f'error decoding txn: {e} -- raw txn:{os.linesep}{txn}')

