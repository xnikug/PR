import threading
from collections import defaultdict
from typing import Dict


class CounterService:
    
    def __init__(self):
        self._counter: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def increment(self, file_path: str) -> int:

        with self._lock:
            self._counter[file_path] += 1
            return self._counter[file_path]
    
    def get_count(self, file_path: str) -> int:

        with self._lock:
            return self._counter.get(file_path, 0)
    
    def get_all_counts(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counter)


class UnsafeCounterService:
    
    def __init__(self, delay: float = 0.01):
        self._counter: Dict[str, int] = defaultdict(int)
        self._delay = delay
    
    def increment(self, file_path: str) -> int:
        import time
        
        # Read current value
        current = self._counter[file_path]
        
        # Delay to force race condition
        time.sleep(self._delay)
        
        # Increment and write back
        self._counter[file_path] = current + 1
        
        return self._counter[file_path]
    
    def get_count(self, file_path: str) -> int:
        return self._counter.get(file_path, 0)
    
    def get_all_counts(self) -> Dict[str, int]:
        return dict(self._counter)
