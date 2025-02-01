import time
import os
import heapq
from collections import deque
from dotenv import load_dotenv

load_dotenv()


class LoadBalancer:
    def __init__(self):
        """
        Initialize:
          - Load per-model usage limits.
          - Load API keys from environment variables.
          - Create per-key usage deques (to track timestamps).
          - Initialize a heap per model to track (stale) usage counts.
        """
        self.model_usage_limits_per_minute = {
            "gemini-1.5-pro": 2,
            "gemini-1.5-flash": 15,
            "gemini-2.0-flash-exp": 10,
            "gemini-exp-1206": 5,
        }

        # Load API keys from environment variables.
        self.api_keys = []
        for idx in range(10):
            key = os.getenv(f"GEMINI_API_KEY_{idx}")
            if key:
                self.api_keys.append(key)
        print(f"Found {len(self.api_keys)} API keys for Gemini.")
        self.api_keys = self.api_keys[::-1]

        # Build the usage_counter:
        # for each API key and each model, create a deque to store timestamps.
        self.usage_counter = {
            api_key: {model: deque() for model in self.model_usage_limits_per_minute}
            for api_key in self.api_keys
        }

        # Allow a little extra time beyond 60 seconds.
        self.time_limit_to_deque = 65

        # For each model, build a heap of (usage_count, tie, api_key).
        # All API keys start with a usage count of 0.
        self.model_heaps = {}
        self._tie_counter = 0  # used as a tie-breaker to guarantee stable ordering

        for model in self.model_usage_limits_per_minute:
            heap = []
            for api_key in self.api_keys:
                entry = (0, self._tie_counter, api_key)
                self._tie_counter += 1
                heap.append(entry)
            heapq.heapify(heap)
            self.model_heaps[model] = heap

    def _purge_old_requests(self, usage_deque, current_time):
        """
        Remove timestamps from usage_deque older than the allowed time window.
        """
        while usage_deque and usage_deque[0] <= current_time - self.time_limit_to_deque:
            usage_deque.popleft()

    def getAvailableAPIKey(self, model_name):
        """
        Return an API key for the given model_name that:
          - Is below the per-minute usage limit.
          - Is the least occupied of all available keys.
        If no key is available, return None.
        """
        current_time = time.time()
        usage_limit = self.model_usage_limits_per_minute.get(model_name, 0)
        if usage_limit == 0:
            return None  # Either unknown model or the limit is set to 0.

        # Get the heap for this model.
        heap = self.model_heaps.get(model_name)
        if not heap:
            return None

        # Lazy-update loop: pop stale entries and update their usage counts.
        tried = 0
        num_keys = len(heap)
        while tried < num_keys:
            stored_usage, tie, api_key = heapq.heappop(heap)
            usage_deque = self.usage_counter[api_key][model_name]
            self._purge_old_requests(usage_deque, current_time)
            actual_usage = len(usage_deque)

            # If the stored count is stale, push an updated count and try again.
            if actual_usage != stored_usage:
                heapq.heappush(heap, (actual_usage, tie, api_key))
                tried += 1
                continue

            # If this key is within the usage limit, use it.
            if actual_usage < usage_limit:
                usage_deque.append(current_time)
                new_usage = actual_usage + 1
                heapq.heappush(heap, (new_usage, tie, api_key))
                print(f"Selected key '{api_key}' with usage {actual_usage} for model '{model_name}'.")
                return api_key
            else:
                # The key is at or above its limit. Push it back and try next.
                heapq.heappush(heap, (actual_usage, tie, api_key))
                tried += 1
                # If the smallest count in the heap is at limit or higher, exit early.
                if heap[0][0] >= usage_limit:
                    return None
        return None


if __name__ == "__main__":
    # Example usage:
    balancer = LoadBalancer()

    # Try retrieving keys for a given model multiple times.
    model = "gemini-1.5-pro"
    for i in range(5):
        key = balancer.getAvailableAPIKey(model)
        if key:
            print(f"[{i+1}] Got key: {key}")
        else:
            print(f"[{i+1}] No available key for model '{model}' right now.")