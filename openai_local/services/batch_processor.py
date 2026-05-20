"""
Batch Processor for LLM requests.
Collects incoming requests and processes them in batches for higher throughput.
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import deque
import time


@dataclass
class BatchRequest:
    """A single request waiting to be batched"""
    prompt: str
    generation_kwargs: Dict[str, Any]
    future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())
    created_at: float = field(default_factory=time.time)


class BatchProcessor:
    """
    Collects requests and processes them in batches.
    
    When a request comes in:
    1. Add it to the pending queue
    2. Wait for batch to fill OR timeout
    3. Process all pending requests together
    4. Return results to each requester
    """
    
    def __init__(
        self,
        llm_model,
        max_batch_size: int = 4,
        batch_timeout_ms: int = 100,  # Max wait time before processing partial batch
    ):
        self.llm_model = llm_model
        self.max_batch_size = max_batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.pending_requests: deque[BatchRequest] = deque()
        self._lock = asyncio.Lock()
        self._processing = False
        self._processor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the background batch processor"""
        if self._processor_task is None:
            self._processor_task = asyncio.create_task(self._batch_processor_loop())
            print(f"🔄 Batch processor started (max_batch={self.max_batch_size}, timeout={self.batch_timeout_ms}ms)")
    
    async def stop(self):
        """Stop the batch processor"""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
    
    async def submit(self, prompt: str, generation_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a request for batched processing.
        Returns the result when the batch is processed.
        """
        # Create a future to wait for the result
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        request = BatchRequest(
            prompt=prompt,
            generation_kwargs=generation_kwargs,
            future=future
        )
        
        async with self._lock:
            self.pending_requests.append(request)
        
        # Wait for the result
        result = await future
        return result
    
    async def _batch_processor_loop(self):
        """Background loop that processes batches"""
        while True:
            try:
                # Wait for requests or timeout
                await asyncio.sleep(self.batch_timeout_ms / 1000)
                
                # Check if we have pending requests
                async with self._lock:
                    if not self.pending_requests:
                        continue
                    
                    # Collect batch
                    batch: List[BatchRequest] = []
                    while self.pending_requests and len(batch) < self.max_batch_size:
                        batch.append(self.pending_requests.popleft())
                
                if batch:
                    await self._process_batch(batch)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Batch processor error: {e}")
                # Complete any pending futures with error
                async with self._lock:
                    while self.pending_requests:
                        req = self.pending_requests.popleft()
                        if not req.future.done():
                            req.future.set_exception(e)
    
    async def _process_batch(self, batch: List[BatchRequest]):
        """Process a batch of requests together"""
        if not batch:
            return
        
        try:
            # Extract prompts and find common generation kwargs
            prompts = [req.prompt for req in batch]
            
            # Use kwargs from first request (they should be similar)
            # In production, you'd want to group by similar kwargs
            base_kwargs = batch[0].generation_kwargs.copy()
            
            # Remove streaming flag for batch processing
            base_kwargs.pop("stream", None)
            
            print(f"📦 Processing batch of {len(prompts)} requests...")
            
            # Run batch inference in thread pool
            results = await asyncio.to_thread(
                self._run_batch_inference,
                prompts,
                base_kwargs
            )
            
            # Distribute results to futures
            for i, req in enumerate(batch):
                if i < len(results):
                    if not req.future.done():
                        req.future.set_result(results[i])
                else:
                    if not req.future.done():
                        req.future.set_exception(Exception("No result for request"))
                        
            print(f"✅ Batch processed successfully")
            
        except Exception as e:
            print(f"❌ Batch processing error: {e}")
            # Set exception on all futures
            for req in batch:
                if not req.future.done():
                    req.future.set_exception(e)
    
    def _run_batch_inference(self, prompts: List[str], generation_kwargs: Dict[str, Any]) -> List[Dict]:
        """Run batch inference (blocking, runs in thread pool)"""
        results = []
        
        # llama-cpp-python supports batch inference via list of prompts
        # BUT only in create_completion, not in __call__
        # We'll use create_completion for batching
        
        try:
            # Try batch inference first
            batch_result = self.llm_model.create_completion(
                prompt=prompts,
                **generation_kwargs
            )
            
            # batch_result is a list when multiple prompts are provided
            if isinstance(batch_result, list):
                results = batch_result
            else:
                # Single result, wrap it
                results = [batch_result]
                
        except Exception as e:
            # Fallback to sequential processing if batch fails
            print(f"⚠️ Batch inference failed, falling back to sequential: {e}")
            for prompt in prompts:
                try:
                    result = self.llm_model(prompt, **generation_kwargs)
                    results.append(result)
                except Exception as inner_e:
                    results.append({"error": str(inner_e)})
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current batch processor statistics"""
        return {
            "pending_requests": len(self.pending_requests),
            "max_batch_size": self.max_batch_size,
            "batch_timeout_ms": self.batch_timeout_ms,
            "is_running": self._processor_task is not None and not self._processor_task.done()
        }
