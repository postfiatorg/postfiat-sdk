import heapq
from typing import AsyncIterator, TypeVar

T = TypeVar('T')

async def combine_streams(*streams: list[AsyncIterator[T]], dedup: bool = True) -> AsyncIterator[T]:
    heap = []
    last_item = None # used to dedup the stream
    
    # i is used as an ordering tiebreaker to avoid trying to compare stream objects
    for i, stream in enumerate(streams):
        try:
            item = await anext(stream)
            heapq.heappush(heap, (item, i, stream))
        except StopAsyncIteration:
            pass
    
    while heap:
        item, i, stream = heapq.heappop(heap)
        if item != last_item:
            yield item
            if dedup:
                last_item = item
        
        try:
            next_item = await anext(stream)
            heapq.heappush(heap, (next_item, i, stream))
        except StopAsyncIteration:
            pass

