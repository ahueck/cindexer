import json
from abc import ABC, abstractmethod
from typing import List
from .models import TypeInfo


class Formatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def output(self, type_infos: List[TypeInfo], show_location: bool):
        pass


class TextFormatter(Formatter):
    """Output results in a human-readable, line-by-line format."""

    def output(self, type_infos: List[TypeInfo], show_location: bool):
        grouped = {"UserDefined": [], "Alias": []}
        for info in type_infos:
            grouped.setdefault(info.category, []).append(info)

        for category, items in grouped.items():
            print(f"--- {category} ---")
            if not items:
                print("  (None found)")
                continue

            for item in sorted(items, key=lambda x: x.name):
                loc_str = ""
                if show_location:
                    loc_str = f" @ {item.filename}:{item.line}"

                def_str = "[Def]" if item.is_definition else "[Decl]"
                print(f"  {item.kind}: {item.name} {def_str}{loc_str}")
            print("")


class JsonFormatter(Formatter):
    """Output results as a generic JSON object."""

    def output(self, type_infos: List[TypeInfo], show_location: bool):
        data = [t.to_dict() for t in type_infos]
        if not show_location:
            for item in data:
                del item["location"]

        print(json.dumps(data, indent=2))
