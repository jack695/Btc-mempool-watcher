import time
from collections.abc import MutableMapping
from typing import Any, Iterator, Optional


class Cache(MutableMapping):
    """
    A dictionary-like cache where each entry expires after a set time (TTL).

    Args:
        default_ttl (int): Default time-to-live for each cache entry in seconds.
    """

    def __init__(self, default_ttl: int = 60) -> None:
        self._store: dict[Any, tuple[Any, float]] = {}
        self._default_ttl: int = default_ttl

    # === PUBLIC METHODS ===

    def cleanup(self) -> None:
        """
        Remove all expired entries from the cache.
        """
        expired_keys = [key for key in self._store if self._is_expired(key)]
        for key in expired_keys:
            self._store.pop(key, None)

    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a key with a specific TTL.

        Args:
            key (Any): The key to insert.
            value (Any): The value to associate with the key.
            ttl (Optional[int]): Custom time-to-live in seconds. Defaults to default_ttl.
        """
        expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._store[key] = (value, expiry)

    def get(self, key: Any, default: Any = None) -> Any:
        """
        Get a key if it exists and is not expired, else return default.

        Args:
            key (Any): The key to retrieve.
            default (Any): Value to return if key is missing or expired.

        Returns:
            Any: The value associated with the key, or default if missing/expired.

        Raises:
            KeyError: If the internal __getitem__ raises because key expired or is missing.
        """
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    # === PROTECTED METHODS ===

    def _is_expired(self, key: Any) -> bool:
        """
        Check if a given key has expired.

        Args:
            key (Any): The key to check.

        Returns:
            bool: True if expired or missing, False otherwise.
        """
        if key not in self._store:
            return True
        _, expiry = self._store[key]
        return time.time() > expiry

    # === PRIVATE/SPECIAL METHODS ===

    def __getitem__(self, key: Any) -> Any:
        """
        Get an item by key. Raises KeyError if expired or missing.

        Args:
            key (Any): The key to retrieve.

        Returns:
            Any: The value associated with the key.

        Raises:
            KeyError: If the key does not exist or has expired.
        """
        if self._is_expired(key):
            self._store.pop(key, None)
            raise KeyError(f"Key '{key}' has expired")
        value, _ = self._store[key]
        return value

    def __setitem__(self, key: Any, value: Any) -> None:
        """
        Set an item with the default TTL.

        Args:
            key (Any): The key to insert.
            value (Any): The value to associate with the key.
        """
        expiry = time.time() + self._default_ttl
        self._store[key] = (value, expiry)

    def __delitem__(self, key: Any) -> None:
        """
        Delete an item by key.

        Args:
            key (Any): The key to delete.

        Raises:
            KeyError: If the key does not exist.
        """
        del self._store[key]

    def __iter__(self) -> Iterator[Any]:
        """
        Iterate over non-expired keys.

        Returns:
            Iterator[Any]: An iterator over non-expired keys.
        """
        self.cleanup()
        return iter(self._store)

    def __len__(self) -> int:
        """
        Get the number of non-expired items.

        Returns:
            int: The number of valid (non-expired) entries.
        """
        self.cleanup()
        return len(self._store)

    def __contains__(self, key: Any) -> bool:
        """
        Check if a key exists and is not expired.

        Args:
            key (Any): The key to check.

        Returns:
            bool: True if the key exists and is valid, False otherwise.
        """
        if self._is_expired(key):
            self._store.pop(key, None)
            return False
        return key in self._store


# Example usage
if __name__ == "__main__":
    cache = ExpiringCache(default_ttl=5)
    cache["foo"] = "bar"
    print(cache["foo"])  # -> 'bar'
    print("foo" in cache)  # -> True
    time.sleep(6)
    cache.cleanup()
    print("foo" in cache)  # -> False
    print(cache.get("foo", "default"))  # -> 'default'
