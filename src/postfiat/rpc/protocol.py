from typing import AsyncIterator, Protocol

from postfiat.models.transaction import Transaction


class Client(Protocol):

    async def get_account_txns(
        self,
        account: str,
        start_ledger: int,
        end_ledger: int,
    ) -> AsyncIterator[Transaction]:
        ...