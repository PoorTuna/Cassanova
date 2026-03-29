from asyncio import create_subprocess_exec, subprocess, wait_for


async def execute_tool(
    tool_path: str,
    resolved_args: list[str],
    workdir: str | None = None,
    timeout: int = 30,
    stdout: int = subprocess.PIPE,
    stderr: int = subprocess.PIPE,
) -> tuple[str, str, int | None]:
    process = await create_subprocess_exec(
        tool_path, *resolved_args, stdout=stdout, stderr=stderr, cwd=workdir
    )
    stdout, stderr = await wait_for(process.communicate(), timeout=timeout)  # type: ignore[arg-type]

    return stdout.decode(), stderr.decode(), process.returncode  # type: ignore[attr-defined]
