import os
from typing import List, Dict, Optional, Tuple
from .models import CacheEntry, DependencyInfo, TypeInfo


class TranslationUnitCache:
    """
    Manages caching of parsed translation units.
    Validates cache entries based on file modification times.
    """

    def __init__(self):
        self._cache: Dict[Tuple[str, Tuple[str, ...]], CacheEntry] = {}

    def get(self, source_path: str, signature: Tuple[str, ...]) -> Optional[CacheEntry]:
        key = (source_path, signature)
        entry = self._cache.get(key)
        if not entry:
            return None

        try:
            current_mtime = os.path.getmtime(source_path)
        except OSError:
            # Handle deleted file
            del self._cache[key]
            return None

        if current_mtime != entry.source_mtime:
            # Invalidate if modified
            del self._cache[key]
            return None

        for dep_path, dep_info in entry.dependencies.items():
            # Skip system headers per requirements
            if dep_info.is_system:
                continue

            try:
                dep_mtime = os.path.getmtime(dep_path)
                if dep_mtime != dep_info.mtime:
                    del self._cache[key]
                    return None
            except OSError:
                del self._cache[key]
                return None

        return entry

    def put(
        self,
        source_path: str,
        signature: Tuple[str, ...],
        type_infos: List[TypeInfo],
        dependencies: Dict[str, DependencyInfo],
    ):
        try:
            source_mtime = os.path.getmtime(source_path)
        except OSError:
            return

        entry = CacheEntry(
            source_path=source_path,
            compile_signature=signature,
            source_mtime=source_mtime,
            type_infos=type_infos,
            dependencies=dependencies,
        )
        self._cache[(source_path, signature)] = entry

    def clear(self):
        """Clears the entire cache."""
        self._cache.clear()

    def remove(self, source_path: str, signature: Tuple[str, ...]) -> bool:
        """
        Removes a specific entry from the cache.
        Returns True if the entry existed and was removed, False otherwise.
        """
        key = (source_path, signature)
        if key in self._cache:
            del self._cache[key]
            return True
        return False
