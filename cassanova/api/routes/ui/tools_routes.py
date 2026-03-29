from typing import Any

from fastapi import APIRouter
from fastapi.requests import Request

from cassanova.api.dependencies.db_session import get_session
from cassanova.consts.cass_tools import CassTools
from cassanova.web.template_config import templates

cassanova_ui_tools_router = APIRouter(tags=["UI"])


@cassanova_ui_tools_router.get("/cluster/{cluster_name}/tools/cqlsh")
def cqlsh_devtools(request: Request, cluster_name: str) -> Any:
    session = get_session(cluster_name)

    return templates.TemplateResponse(
        "cqlsh.html",
        {
            "request": request,
            "cluster_config_entry": cluster_name,
            "cluster_name": session.cluster.metadata.cluster_name,
        },
    )


@cassanova_ui_tools_router.get("/tools")
def tool_hub(request: Request) -> Any:
    return templates.TemplateResponse(
        "tools.html",
        {
            "request": request,
            "tools": sorted(CassTools.ALLOWED_TOOLS),
        },
    )
