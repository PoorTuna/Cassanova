from asyncio import subprocess, create_subprocess_exec, wait_for
from typing import Optional


async def execute_tool(tool_path: str, resolved_args: list[str], workdir: Optional[str] = None, timeout: int = 30,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE) -> tuple[str, str, int | None]:
    process = await create_subprocess_exec(
        tool_path, *resolved_args,
        stdout=stdout,
        stderr=stderr,
        cwd=workdir
    )
    stdout, stderr = await wait_for(process.communicate(), timeout=timeout)

    return stdout.decode(), stderr.decode(), process.returncode
