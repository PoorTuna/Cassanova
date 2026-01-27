from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from cassanova.api.dependencies.auth import create_access_token, get_current_user, authenticate_user
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.web.template_config import templates

login_router = APIRouter()


@login_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@login_router.post("/login")
async def login_web(username: str = Form(...), password: str = Form(...)):
    user = await authenticate_user(username, password)
    config = get_clusters_config()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.username, "roles": user.roles})
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=config.auth.session_expire_minutes * 60,
        expires=config.auth.session_expire_minutes * 60,
        samesite="lax",
        secure=False
    )
    return response


@login_router.post("/api/v1/login")
async def login_api(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    access_token = create_access_token(data={"sub": user.username, "roles": user.roles})
    return {"access_token": access_token, "token_type": "bearer"}


@login_router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response
