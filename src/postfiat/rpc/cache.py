from bisect import insort
import json
import os
import re
import tempfile
from typing import AsyncIterator, NamedTuple
import logging

import aiofiles

from postfiat.models.transaction import Transaction
from postfiat.nodes.task.constants import EARLIEST_LEDGER_SEQ
from postfiat.rpc.network import RpcClient
from postfiat.rpc.protocol import Client
from postfiat.rpc.errors import CacheError

log = logging.getLogger(__name__)

REGEX_LEDGER_RANGE = re.compile(r'(\d+)-(\d+)\.jsonl$')

class LedgerRange(NamedTuple):
    start: int
    end: int


def ledger_range_from_filename(filename: str) -> LedgerRange:
    match = REGEX_LEDGER_RANGE.match(filename)
    if match:
        start_ledger, end_ledger = map(int, match.groups())
        return LedgerRange(start_ledger, end_ledger)
    raise CacheError(f"invalid filename: {filename}")


def filename_from_ledger_range(ledger_range: LedgerRange) -> str:
    return f"{ledger_range.start}-{ledger_range.end}.jsonl"


class AccountTxnCache():

    def __init__(self, dirpath: str, client: Client, account: str):
        self.dirpath = dirpath
        self.client = client
        self.account = account
        os.makedirs(self.path, exist_ok=True)
        self.ranges = []
        for filename in os.listdir(self.path):
            try:
                ledger_range = ledger_range_from_filename(filename)
                self.ranges.append(ledger_range)
            except CacheError:
                log.warning(f"Skipping invalid cache file: {filename}")
        self.ranges.sort()

    async def check_and_fix_total_range(self) -> None:
        log.debug(f"Checking total range gaps for {self.account}")
        for i in range(1, len(self.ranges)):
            prev_end = self.ranges[i-1].end
            start = self.ranges[i].start
            if start > prev_end + 1:
                log.info(f"Found gap from {prev_end+1} to {start-1}, downloading...")
                await self.download_ledger_range(prev_end+1, start-1)

    @property
    def total_range(self) -> LedgerRange:
        if not self.ranges:
            return LedgerRange(EARLIEST_LEDGER_SEQ, -1)
        return LedgerRange(self.ranges[0].start, self.ranges[-1].end)

    async def download_latest(self):
        start = max(self.total_range.end+1, EARLIEST_LEDGER_SEQ)
        log.info(f"Downloading latest transactions for {self.account} from ledger {start}")
        await self.download_ledger_range(start, -1)

    async def download_ledger_range(self, start_ledger: int, end_ledger: int):
        log.info(f"Downloading ledger range {start_ledger}-{end_ledger} for {self.account}")
        actual_end_ledger = start_ledger
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            async for txn in self.client.get_account_txns(self.account, start_ledger, end_ledger):
                actual_end_ledger = txn.ledger_index
                temp_file.write(json.dumps(txn.data) + os.linesep)
        log.debug(f"Download complete, actual end ledger: {actual_end_ledger}")
        os.rename(temp_file.name, self.range_path(start_ledger, actual_end_ledger))
        insort(self.ranges, LedgerRange(start_ledger, actual_end_ledger))

    def range_path(self, start_ledger: int, end_ledger: int) -> str:
        return os.path.join(self.path, filename_from_ledger_range(LedgerRange(start_ledger, end_ledger)))

    async def get_txns_from_file(self, path: str) -> AsyncIterator[Transaction]:
        async with aiofiles.open(path, 'r') as f:
            async for line in f:
                yield Transaction.from_raw_json(line)

    async def get_txns(self, start_ledger: int, end_ledger: int) -> AsyncIterator[Transaction]:
        log.info(f"Getting transactions for {self.account} from {start_ledger} to {end_ledger}")
        await self.check_and_fix_total_range()
        
        if end_ledger == -1 or end_ledger > self.total_range.end:
            log.debug(f"Current total range ends at {self.total_range.end}, downloading latest")
            await self.download_latest()
            
        if start_ledger < self.total_range.start or end_ledger > self.total_range.end:
            raise CacheError(f"requested range {start_ledger}-{end_ledger} is outside of total available range {self.total_range.start}-{self.total_range.end}")

        relevant_ranges = []
        for r in self.ranges:
            if r.end < start_ledger:
                continue
            if end_ledger != -1 and r.start > end_ledger:
                break
            relevant_ranges.append(r)
        
        log.debug(f"Found {len(relevant_ranges)} relevant ranges to search")
        for path in (self.range_path(r.start, r.end) for r in relevant_ranges):
            log.debug(f"Reading transactions from {path}")
            async for txn in self.get_txns_from_file(path):
                if txn.ledger_index >= start_ledger and (end_ledger == -1 or txn.ledger_index <= end_ledger):
                    yield txn

    @property
    def path(self) -> str:
        return os.path.join(self.dirpath, self.account)


class TxnCache():

    def __init__(self, dirpath: str, client: Client):
        self.dirpath = dirpath
        self.client = client
        self.accounts = {}

    def get_account_txns(self,
                         account: str,
                         start_ledger: int = EARLIEST_LEDGER_SEQ,
                         end_ledger: int = -1,
    ) -> AsyncIterator[Transaction]:
        if account not in self.accounts:
            self.accounts[account] = AccountTxnCache(self.dirpath, self.client, account)
        return self.accounts[account].get_txns(start_ledger, end_ledger)
    

class CachingRpcClient():

    def __init__(self, endpoint: str, cache_dir: str):
        self.rpc_client = RpcClient(endpoint)
        self.cache = TxnCache(cache_dir, self.rpc_client)

    def get_account_txns(self,
                         account: str,
                         start_ledger: int = EARLIEST_LEDGER_SEQ,
                         end_ledger: int = -1,
    ) -> AsyncIterator[Transaction]:
        log.info(f"CachingRpcClient: Getting transactions for {account} from {start_ledger} to {end_ledger}")
        return self.cache.get_account_txns(account, start_ledger, end_ledger)