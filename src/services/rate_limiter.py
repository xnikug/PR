import time
import threading
from collections import defaultdict
from typing import List, Dict, Tuple


class RateLimiter:    
    def __init__(self, max_requests: int = 5, time_window: float = 1.0):
        self._max_requests = max_requests
        self._time_window = time_window
        self._request_timestamps: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        current_time = time.time()
        
        with self._lock:
            # Get request timestamps for this IP
            timestamps = self._request_timestamps[client_ip]
            
            # Remove old timestamps outside the window
            timestamps[:] = [
                ts for ts in timestamps 
                if current_time - ts < self._time_window
            ]
            
            # Check if under limit
            if len(timestamps) < self._max_requests:
                timestamps.append(current_time)
                remaining = self._max_requests - len(timestamps)
                return True, remaining
            else:
                return False, 0
    
    def get_stats(self, client_ip: str) -> Dict[str, int]:
        
        with self._lock:
            timestamps = self._request_timestamps.get(client_ip, [])
            current_time = time.time()
            recent = [ts for ts in timestamps if current_time - ts < self._time_window]
            
            return {
                'requests_in_window': len(recent),
                'max_requests': self._max_requests,
                'remaining': max(0, self._max_requests - len(recent))
            }
