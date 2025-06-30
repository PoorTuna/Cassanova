from http import HTTPStatus
from json import dumps
from shutil import rmtree
from typing import List, Optional, Literal

from fastapi import APIRouter
from fastapi import UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import generate_cluster_connection, ClusterConnectionConfig
from cassanova.consts.cass_tools import CassTools
from cassanova.core.cql.execute_query import execute_query_cql
from cassanova.core.tools.argument_handling import parse_args, resolve_args
from cassanova.core.tools.execute_tool import execute_tool
from cassanova.core.tools.tool_validation import is_tool_allowed, get_tool_path
from cassanova.core.tools.user_workspace import save_uploaded_files, get_namespace_dir
from cassanova.models.cql_query import CQLQuery

clusters_config = get_clusters_config()
cassanova_api_post_router = APIRouter()


@cassanova_api_post_router.post("/cluster/{cluster_name}/operations/cqlsh")
def delete_table(cluster_name: str, query: CQLQuery):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()
    result = execute_query_cql(session, query)
    try:
        serialized_result = dumps(result)
    except (UnicodeDecodeError, TypeError) as e:
        serialized_result = str(result)
    return serialized_result


@cassanova_api_post_router.post("/tool/run")
async def run_tool(
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
