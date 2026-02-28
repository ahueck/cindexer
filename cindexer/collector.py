import os
from typing import List, Optional, Tuple
from clang.cindex import CursorKind
from .models import TypeInfo


class TypeCollector:
    """
    Stateful visitor that traverses the AST to collect type information.
    """

    USER_DEFINED_KINDS = {
        CursorKind.STRUCT_DECL: "Struct",
        CursorKind.CLASS_DECL: "Class",
        CursorKind.UNION_DECL: "Union",
        CursorKind.ENUM_DECL: "Enum",
        CursorKind.CLASS_TEMPLATE: "TemplateClass",
    }

    ALIAS_KINDS = {
        CursorKind.TYPEDEF_DECL: "Typedef",
        CursorKind.TYPE_ALIAS_DECL: "Using",
    }

    def __init__(
        self,
        tu_source: str,
        exclude_system_headers: bool = False,
        system_paths: Optional[List[str]] = None,
    ):
        self.tu_source = tu_source
        self.collected_types: List[TypeInfo] = []
        self.exclude_system_headers = exclude_system_headers
        self.system_paths = system_paths or []

    def _get_category_and_kind(self, cursor) -> Tuple[Optional[str], Optional[str]]:
        if cursor.kind in self.USER_DEFINED_KINDS:
            return "UserDefined", self.USER_DEFINED_KINDS[cursor.kind]
        if cursor.kind in self.ALIAS_KINDS:
            return "Alias", self.ALIAS_KINDS[cursor.kind]
        return None, None

    def collect(self, cursor):
        """
        Traverse AST and populate collected_types list with TypeInfo objects.
        Extracts ALL named types without filtering.
        """
        if self.exclude_system_headers:
            # Check if in system header (libclang check)
            if cursor.location.is_in_system_header:
                return
            if cursor.location.file:
                filename = cursor.location.file.name
                for sys_path in self.system_paths:
                    if filename == sys_path or filename.startswith(sys_path + os.sep):
                        return

        if cursor.location.file:
            category, kind = self._get_category_and_kind(cursor)

            if category and kind and cursor.spelling:
                self.collected_types.append(
                    TypeInfo.from_cursor(cursor, category, kind, self.tu_source)
                )

        for child in cursor.get_children():
            self.collect(child)
