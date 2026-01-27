from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from cassanova.web.template_config import templates

node_recovery_ui_router = APIRouter(prefix='/node-recovery', tags=['Node Recovery UI'])


@node_recovery_ui_router.get('', response_class=HTMLResponse)
async def node_recovery_dashboard(request: Request):
    return templates.TemplateResponse(
        name='node_recovery.html',
        context={'request': request}
    )
