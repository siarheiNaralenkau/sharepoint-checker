import re
from functools import lru_cache


@lru_cache(maxsize=32)
def compile_pattern(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def matches_any(value: str, patterns: list[str]) -> bool:
    return any(re.search(p, value) for p in patterns)


def is_project_folder(name: str, regex: str) -> bool:
    return bool(compile_pattern(regex).match(name))
