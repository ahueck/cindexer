from typing import List
from .models import TypeInfo


class TypeFilter:
    """
    Applies query-time filters to a list of TypeInfo objects.
    """

    @staticmethod
    def filter(
        type_infos: List[TypeInfo],
        scope: str,
        decls: str,
        main_file: str,
    ) -> List[TypeInfo]:
        filtered = []
        for info in type_infos:
            if info.name.startswith("_"):
                continue

            if scope == "main":
                if info.filename != main_file:
                    continue

            if decls == "defs":
                if not info.is_definition:
                    continue

            filtered.append(info)
        return filtered
