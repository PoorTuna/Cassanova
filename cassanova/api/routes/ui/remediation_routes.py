from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from cassanova.web.template_config import templates

remediation_ui_router = APIRouter(prefix='/remediation', tags=['Remediation UI'])


@remediation_ui_router.get('', response_class=HTMLResponse)
async def remediation_dashboard(request: Request):
    return templates.TemplateResponse(
        name='remediation.html',
        context={'request': request}
    )
