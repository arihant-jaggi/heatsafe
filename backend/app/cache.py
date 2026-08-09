from functools import lru_cache
import time

class TTLCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self.store = {}

    def get(self, key):
        v = self.store.get(key)
        if not v:
            return None
        value, exp = v
        if time.time() > exp:
            self.store.pop(key, None)
            return None
        return value

    def set(self, key, value):
        self.store[key] = (value, time.time() + self.ttl)

geocode_cache = TTLCache(ttl_seconds=24 * 3600)
route_cache = TTLCache(ttl_seconds=6 * 3600)
