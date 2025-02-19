from postfiat.models.transaction import Transaction
from postfiat.nodes.task.models.messages import Message


def encode_account_msg(message: Message) -> list[Transaction]:
    raise NotImplementedError('TODO move task txn encoding here')
