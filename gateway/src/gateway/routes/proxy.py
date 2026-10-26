from fastapi import APIRouter, HTTPException, Request

from gateway.config import COOKIE_ROUTES

router = APIRouter(prefix="/api")


@router.api_route(
    "/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(service: str, path: str, request: Request):
    config = request.app.state.services.get(service)
    if config is None:
        raise HTTPException(404, "Service not found")
    headers = request.app.state.auth.create_headers(
        request=request, service=service, path=path, config=config
    )
    route = (service, path.strip("/"), request.method)
    return await request.app.state.proxy.forward(
        request=request,
        base_url=config.url,
        path=path,
        headers=headers,
        forward_cookies=route in COOKIE_ROUTES,
    )
