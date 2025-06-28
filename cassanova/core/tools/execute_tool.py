from subprocess import run, PIPE
from typing import List


def execute_tool(tool_path: str, args: List[str], timeout: int = 30):
    return run(
        [tool_path] + args,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        timeout=timeout,
        env={}
    )
