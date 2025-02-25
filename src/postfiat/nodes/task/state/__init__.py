from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
import os

from postfiat.nodes.task.models.messages import (
    Message, TaskMessage, Direction,
    UserGDocContextMessage, UserInitiationRiteMessage,
    UserLogMessage, NodeLogResponseMessage,
    NodeWalletFundingMessage, NodeInitiationRewardMessage, Scope,
    UserRequestMessage, NodeProposalMessage, UserAcceptanceMessage,
    UserRefusalMessage, UserCompletionMessage, NodeChallengeMessage,
    UserChallengeResponseMessage, NodeRewardMessage,
    UserSweepAddressMessage, NodeBlacklistMessage,
)

class AccountStatus(Enum):
    INVALID = auto()
    PENDING = auto()
    ACTIVE = auto()
    BLACKLISTED = auto()

class RiteStatus(Enum):
    INVALID = auto()
    UNSTARTED = auto()
    UNDERWAY = auto()
    COMPLETE = auto()

class TaskStatus(Enum):
    INVALID = auto()
    REQUESTED = auto()
    PROPOSED = auto()
    ACCEPTED = auto()
    REFUSED = auto()
    COMPLETED = auto()
    CHALLENGED = auto()
    RESPONDED = auto()
    REWARDED = auto()

class LogStatus(Enum):
    INVALID = auto()
    LOGGED = auto()
    REQUESTED = auto()
    RESPONDED = auto()

@dataclass
class TaskState:
    status: TaskStatus = TaskStatus.INVALID
    task_request: str | None = None
    task_statement: str | None = None
    completion_statement: str | None = None
    challenge_statement: str | None = None
    challenge_response: str | None = None
    pft_offered: Decimal | None = None
    pft_rewarded: Decimal | None = None
    message_history: list[(datetime, Direction, str)] = field(default_factory=list)

    def update(self, msg: TaskMessage):
        self.message_history.append((msg.timestamp, msg.direction, msg.raw_data))
        match msg:
            case UserRequestMessage():
                if self.status == TaskStatus.INVALID:
                    self.status = TaskStatus.REQUESTED
                    self.task_request = msg.message
            case NodeProposalMessage():
                if self.status == TaskStatus.REQUESTED:
                    self.status = TaskStatus.PROPOSED
                    self.pft_offered = msg.pft_offer
                    self.task_statement = msg.message
            case UserAcceptanceMessage():
                if self.status == TaskStatus.PROPOSED:
                    self.status = TaskStatus.ACCEPTED
            case UserRefusalMessage():
                if self.status in (
                    TaskStatus.PROPOSED, TaskStatus.ACCEPTED,
                    TaskStatus.COMPLETED, TaskStatus.CHALLENGED
                ):
                    self.status = TaskStatus.REFUSED
            case UserCompletionMessage():
                if self.status == TaskStatus.ACCEPTED:
                    self.status = TaskStatus.COMPLETED
                    self.completion_statement = msg.message
            case NodeChallengeMessage():
                if self.status == TaskStatus.COMPLETED:
                    self.status = TaskStatus.CHALLENGED
                    self.challenge_statement = msg.message
            case UserChallengeResponseMessage():
                if self.status == TaskStatus.CHALLENGED:
                    self.status = TaskStatus.RESPONDED
                    self.challenge_response = msg.message
            case NodeRewardMessage():
                if self.status == TaskStatus.RESPONDED:
                    self.status = TaskStatus.REWARDED
                    #self.pft_rewarded = msg.pft_reward
                    self.pft_rewarded = msg.amount_pft

    def data(self) -> str:
        return f'{os.linesep}'.join(f'{timestamp.date().isoformat()} - {direction}: {data}'
            for timestamp, direction, data in self.message_history)

    def __repr__(self):
        return f"TaskState(status={self.status}, pft_offered={self.pft_offered}, pft_rewarded={self.pft_rewarded})"


@dataclass
class LogState:
    status: LogStatus = LogStatus.INVALID
    timestamp: datetime | None = None
    request: str | None = None
    response: str | None = None

    def __needs_response(self, msg: Message) -> bool:
        return 'ODV' in msg.message

    def update(self, msg: Message):
        match msg:
            case UserLogMessage():
                if self.__needs_response(msg):
                    self.status = LogStatus.REQUESTED
                else:
                    self.status = LogStatus.LOGGED
                self.request = msg.message
                self.timestamp = msg.timestamp
            case NodeLogResponseMessage():
                self.status = LogStatus.RESPONDED
                self.response = msg.message

    def data(self) -> str:
        return f'{self.timestamp.date().isoformat()} - {self.request} -> {self.response}'

    def __repr__(self):
        return f"LogState(status={self.status}, request={self.request}, response={self.response})"

@dataclass
class AccountState:
    init_rite_status: RiteStatus = RiteStatus.UNSTARTED
    init_rite_statement: str | None = None
    context_doc_link: str | None = None
    sweep_address: str | None = None
    is_blacklisted: bool = False
    tasks: dict[str, TaskState] = field(default_factory=lambda: defaultdict(TaskState))
    logs: dict[str, LogState] = field(default_factory=lambda: defaultdict(LogState))
    account_message_history: list[(datetime, Direction, str)] = field(default_factory=list)

    def status(self) -> AccountStatus:
        if self.is_blacklisted:
            return AccountStatus.BLACKLISTED
        elif (
            self.init_rite_status != RiteStatus.COMPLETE
            or self.context_doc_link is None
        ):
            return AccountStatus.PENDING
        else:
            return AccountStatus.ACTIVE

    def update(self, msg: Message):
        status = self.status()
        if status == AccountStatus.BLACKLISTED:
            return

        self.account_message_history.append((msg.timestamp, msg.direction, msg.raw_data))
        if msg.scope == Scope.TASK:
            if status == AccountStatus.ACTIVE:
                self.tasks[msg.task_id].update(msg)
        elif msg.scope == Scope.ACCOUNT:
            match msg:
                case UserGDocContextMessage():
                    self.context_doc_link = msg.gdoc_context_link
                case UserLogMessage() | NodeLogResponseMessage():
                    if status == AccountStatus.ACTIVE:
                        self.logs[msg.message_id].update(msg)
                case UserInitiationRiteMessage():
                    if self.init_rite_status == RiteStatus.UNSTARTED:
                        self.init_rite_status = RiteStatus.UNDERWAY
                        self.init_rite_statement = msg.message
                case NodeWalletFundingMessage():
                    pass
                case NodeInitiationRewardMessage():
                    if self.init_rite_status == RiteStatus.UNDERWAY:
                        self.init_rite_status = RiteStatus.COMPLETE
                case UserSweepAddressMessage():
                    self.sweep_address = msg.sweep_address
                case NodeBlacklistMessage():
                    self.is_blacklisted = True

    def data(self) -> str:
        return f'{os.linesep}'.join(f'{timestamp.date().isoformat()} - {direction}: {data}' for timestamp, direction, data in self.account_message_history)

    def task_data(self) -> str:
        return f'{os.linesep}'.join(task.data() for task in self.tasks.values())

    def log_data(self) -> str:
        return f'{os.linesep}'.join(log.data() for log in self.logs.values())

    def all_data(self) -> str:
        return f'{os.linesep}'.join([
            self.data(),
            self.task_data(),
            self.log_data(),
        ])

    def __repr__(self):
        return f"AccountState(init_rite_status={self.init_rite_status}, context_doc_link={self.context_doc_link}, sweep_address={self.sweep_address}, is_blacklisted={self.is_blacklisted}, tasks={self.tasks})"

@dataclass
class NodeState:
    accounts: dict[str, AccountState] = field(default_factory=lambda: defaultdict(AccountState))
    latest_ledger_seq: tuple[int, int] = (0, 0)

    def update(self, msg: Message):
        self.__update_latest_ledger_seq(msg)
        self.accounts[msg.user_wallet].update(msg)

    def __update_latest_ledger_seq(self, msg: Message):
        latest_ledger_seq, latest_txn_seq = self.latest_ledger_seq
        if msg.ledger_seq > latest_ledger_seq or (msg.ledger_seq == latest_ledger_seq and msg.transaction_seq > latest_txn_seq):
            self.latest_ledger_seq = (msg.ledger_seq, msg.transaction_seq)
        elif msg.ledger_seq == latest_ledger_seq and msg.transaction_seq == latest_txn_seq:
            print(f'duplicate ledger seq for msg {msg.hash}')
        else:
            print(f'out of order ledger seq for msg {msg.hash}')

    def __repr__(self):
        return f"{self.__class__.__name__}(accounts={self.accounts}, latest_ledger_seq={self.latest_ledger_seq})"


@dataclass
class UserState:
    node_account: AccountState = field(default_factory=AccountState)
    latest_ledger_seq: tuple[int, int] = (0, 0)

    def update(self, msg: Message):
        self.__update_latest_ledger_seq(msg)
        self.node_account.update(msg)

    def __update_latest_ledger_seq(self, msg: Message):
        latest_ledger_seq, latest_txn_seq = self.latest_ledger_seq
        if msg.ledger_seq > latest_ledger_seq or (msg.ledger_seq == latest_ledger_seq and msg.transaction_seq > latest_txn_seq):
            self.latest_ledger_seq = (msg.ledger_seq, msg.transaction_seq)
        elif msg.ledger_seq == latest_ledger_seq and msg.transaction_seq == latest_txn_seq:
            print(f'duplicate ledger seq for msg {msg.hash}')
        else:
            print(f'out of order ledger seq for msg {msg.hash}')

    def __repr__(self):
        return f"{self.__class__.__name__}(node_account={self.node_account}, latest_ledger_seq={self.latest_ledger_seq})"
