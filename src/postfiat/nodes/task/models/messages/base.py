from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Self

from pydantic import BaseModel

class Direction(Enum):
    USER_TO_NODE = "user_to_node"
    NODE_TO_USER = "node_to_user"

class Scope(Enum):
    ACCOUNT = "account"
    TASK = "task"

# TODO distinguish inbound and outbound messages?
class Message(ABC, BaseModel):
    user_wallet: str
    node_wallet: str
    amount_pft: Decimal
    timestamp: datetime | None = None
    hash: str | None = None
    raw_data: str | None = None
    ledger_seq: int | None = None
    transaction_seq: int | None = None
    user_pubkey: str | None = None
    node_pubkey: str | None = None

    def __lt__(self, other: Self) -> bool:
        return (self.ledger_seq, self.transaction_seq) < (other.ledger_seq, other.transaction_seq)

    @property
    @abstractmethod
    def direction(self) -> Direction:
        pass

    @property
    @abstractmethod
    def scope(self) -> Scope:
        pass

class UserToNodeMixin():
    @property
    def direction(self) -> Direction:
        return Direction.USER_TO_NODE

class NodeToUserMixin():
    @property
    def direction(self) -> Direction:
        return Direction.NODE_TO_USER

class AccountMixin():
    @property
    def scope(self) -> Scope:
        return Scope.ACCOUNT

class TaskMixin():
    task_id: str

    @property
    def scope(self) -> Scope:
        return Scope.TASK

class UserToNodeMessage(UserToNodeMixin, Message):
    pass

class NodeToUserMessage(NodeToUserMixin, Message):
    pass

class AccountMessage(AccountMixin, Message):
    pass

class TaskMessage(TaskMixin, Message):
    pass
