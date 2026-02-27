from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class TypeInfo:
    """
    Holds structured information about a parsed type.
    Decouples data extraction from output formatting.
    """

    name: str
    usr: str
    kind: str
    category: str
    is_definition: bool
    filename: str
    line: int
    column: int
    tu_source: str

    @staticmethod
    def from_cursor(cursor, category: str, kind: str, tu_source: str) -> "TypeInfo":
        return TypeInfo(
            name=cursor.spelling,
            usr=cursor.get_usr(),
            kind=kind,
            category=category,
            is_definition=cursor.is_definition(),
            filename=cursor.location.file.name if cursor.location.file else "<unknown>",
            line=cursor.location.line,
            column=cursor.location.column,
            tu_source=tu_source,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "usr": self.usr,
            "kind": self.kind,
            "category": self.category,
            "is_definition": self.is_definition,
            "location": {
                "file": self.filename,
                "line": self.line,
                "column": self.column,
            },
            "tu_source": self.tu_source,
        }


@dataclass
class DependencyInfo:
    path: str
    mtime: float
    is_system: bool


@dataclass(frozen=True)
class CacheEntry:
    source_path: str
    compile_signature: Tuple[str, ...]
    source_mtime: float
    type_infos: List[TypeInfo]
    dependencies: Dict[str, DependencyInfo]
