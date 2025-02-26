from decimal import Decimal

from .base import Message, NodeToUserMixin, AccountMixin, TaskMixin, UserToNodeMixin

# Node to User messages
class NodeHandshakeMessage(NodeToUserMixin, AccountMixin, Message):
    pubkey: str

class NodeWalletFundingMessage(NodeToUserMixin, AccountMixin, Message):
    pass

class NodeInitiationRewardMessage(NodeToUserMixin, AccountMixin, Message):
    message: str
    #pft_reward: Decimal

class NodeLogResponseMessage(NodeToUserMixin, AccountMixin, Message):
    message_id: str
    message: str

class NodeProposalMessage(NodeToUserMixin, TaskMixin, Message):
    message: str
    pft_offer: Decimal

class NodeChallengeMessage(NodeToUserMixin, TaskMixin, Message):
    message: str

class NodeRewardMessage(NodeToUserMixin, TaskMixin, Message):
    message: str
    #pft_reward: Decimal

class NodeBlacklistMessage(NodeToUserMixin, AccountMixin, Message):
    message: str

# User to Node messages
class UserHandshakeMessage(UserToNodeMixin, AccountMixin, Message):
    pubkey: str

class UserGDocContextMessage(UserToNodeMixin, AccountMixin, Message):
    pubkey: str
    gdoc_context_link: str

class UserInitiationRiteMessage(UserToNodeMixin, AccountMixin, Message):
    message: str

class UserLogMessage(UserToNodeMixin, AccountMixin, Message):
    message_id: str
    message: str

class UserSweepAddressMessage(UserToNodeMixin, AccountMixin, Message):
    sweep_address: str

class UserRequestMessage(UserToNodeMixin, TaskMixin, Message):
    message: str

class UserAcceptanceMessage(UserToNodeMixin, TaskMixin, Message):
    message: str

class UserRefusalMessage(UserToNodeMixin, TaskMixin, Message):
    message: str

class UserCompletionMessage(UserToNodeMixin, TaskMixin, Message):
    message: str

class UserChallengeResponseMessage(UserToNodeMixin, TaskMixin, Message):
    message: str
