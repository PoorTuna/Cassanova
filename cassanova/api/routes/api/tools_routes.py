from http import HTTPStatus
from shutil import rmtree
from typing import List, Optional, Literal

from fastapi import APIRouter, Depends
from fastapi import UploadFile, File, Form
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from cassanova.api.dependencies.auth import require_permissions
from cassanova.api.dependencies.db_session import get_session
from cassanova.consts.cass_tools import CassTools
from cassanova.core.cql.execute_query import execute_query_cql
from cassanova.core.tools.argument_handling import parse_args, resolve_args
from cassanova.core.tools.execute_tool import execute_tool
from cassanova.core.tools.tool_validation import is_tool_allowed, get_tool_path
from cassanova.core.tools.user_workspace import save_uploaded_files, get_namespace_dir
from cassanova.models.cql_query import CQLQuery

tools_router = APIRouter()


@tools_router.post("/cluster/{cluster_name}/operations/cqlsh")
def run_cqlsh(cluster_name: str, query: CQLQuery, _user=Depends(require_permissions("cluster:admin"))):
    session = get_session(cluster_name)
    result = execute_query_cql(session, query)
    return jsonable_encoder(result, custom_encoder={bytes: lambda var: var.hex()})


@tools_router.get("/tool/list")
def get_available_tools():
    return JSONResponse({'tools': CassTools.ALLOWED_TOOLS})


@tools_router.post("/tool/run")
async def run_tool(
        _user=Depends(require_permissions("cluster:admin")),
        tool: Literal[*CassTools.ALLOWED_TOOLS] = Form(...),
        args: Optional[str] = Form(None),
        namespace: Optional[str] = Form(None),
        files: Optional[List[UploadFile]] = File(None)
):
    workdir, namespace = get_namespace_dir(namespace)
    try:
        if not is_tool_allowed(tool):
            return JSONResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content={"error": f"Tool '{tool}' not allowed"}
            )

        tool_path = get_tool_path(tool)
        if not tool_path:
            return JSONResponse(
                status_code=HTTPStatus.NOT_FOUND,
                content={"error": "Tool not found or not executable"}
            )

        safe_args = parse_args(args)
        saved_paths = await save_uploaded_files(files, workdir) if files else []
        resolved_args = resolve_args(safe_args, workdir)
        stdout, stderr, ret_code = await execute_tool(tool_path, resolved_args, workdir)

        return JSONResponse({
            "namespace": namespace,
            "tool": tool,
            "args": safe_args,
            "saved_path": saved_paths,
            "exit_code": ret_code,
            "stdout": stdout,
            "stderr": stderr,
        })

    except TimeoutError:
        return JSONResponse(
            status_code=HTTPStatus.GATEWAY_TIMEOUT,
            content={"error": "Execution timed out"}
        )
    except ValueError as ve:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content={"error": str(ve)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content={"error": f"Execution failed: {e}"}
        )
    finally:
        try:
            rmtree(workdir)
        except Exception as e:
            return JSONResponse(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content={"error": f"File cleanup failed: {e}"}
            )
