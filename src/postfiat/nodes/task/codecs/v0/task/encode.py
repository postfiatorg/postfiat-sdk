from xrpl.wallet import Wallet

from postfiat.models.transaction import Transaction
from postfiat.nodes.task.codecs.v0.common import encode_account_msg as encode_common_msg
from postfiat.nodes.task.models.messages import Message, Direction, NodeWalletFundingMessage, NodeInitiationRewardMessage, NodeProposalMessage, NodeChallengeMessage, NodeRewardMessage, NodeBlacklistMessage

def encode_account_msg(msg: Message, *, node_account: Wallet | str | None = None, user_account: Wallet | str | None = None) -> list[Transaction]:

    if not isinstance(node_account, Wallet) and msg.direction == Direction.NODE_TO_USER:
        raise ValueError('node_account must be a Wallet instance if message is direction USER_TO_NODE')
    if not isinstance(user_account, Wallet) and msg.direction == Direction.USER_TO_NODE:
        raise ValueError('user_account must be a Wallet instance if message is direction NODE_TO_USER')

    if txns := encode_common_msg(msg, node_account=node_account, user_account=user_account):
        return txns

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
            case NodeWalletFundingMessage():
                return [Transaction(**params,
                                    memo_type='discord_wallet_funding')]

            case NodeInitiationRewardMessage():
                return [Transaction(**params,
                                    memo_type='INITIATION_REWARD',
                                    memo_data=msg.message)]

            case NodeProposalMessage():
                return [Transaction(**params,
                                    memo_data=msg.message,
                                    memo_type=msg.message_id)]

            case NodeChallengeMessage():
                return [Transaction(**params,
                                    memo_data=msg.message,
                                    memo_type=msg.message_id)]

            case NodeRewardMessage():
                return [Transaction(**params,
                                    memo_data=msg.message,
                                    memo_type=msg.message_id)]

            case NodeBlacklistMessage():
                return [Transaction(**params,
                                    memo_data=msg.message,
                                    memo_type='BLACKLIST')]

    # USER TO NODE
    # TODO: move user to node txn encoding here

    return []