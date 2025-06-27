import os
from shlex import split
from typing import Optional, List


def parse_args(arg_string: Optional[str]) -> List[str]:
    return split(arg_string) if arg_string else []


def resolve_args(args: List[str], workdir: str) -> List[str]:
    resolved = []
    for arg in args:
        abs_path = os.path.abspath(os.path.join(workdir, arg))
        if not abs_path.startswith(workdir):
            raise ValueError(f"Illegal path: {arg}")
        resolved.append(abs_path if os.path.exists(abs_path) else arg)
    return resolved
