from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cassanova.exceptions.cql_exceptions import CQLPermissionDenied, ReadOnlyClusterError


def add_cql_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ReadOnlyClusterError)
    async def read_only_handler(_request: Request, exc: ReadOnlyClusterError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": f"Cluster '{exc.cluster_name}' is in read-only mode"},
        )

    @app.exception_handler(CQLPermissionDenied)
    async def permission_denied_handler(
        _request: Request, exc: CQLPermissionDenied
    ) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc)},
        )
