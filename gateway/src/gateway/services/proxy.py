import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response


class GatewayProxyService:
    BLOCKED_RESPONSE_HEADERS = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
    }

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def forward(
        self,
        request: Request,
        base_url: str,
        path: str,
        headers: dict[str, str],
        forward_cookies: bool = False,
    ) -> Response:
        url = f"{base_url.rstrip('/')}/{path}"

        try:
            # Build directly: a shared AsyncClient cookie jar must never
            # attach another browser's cookies to an upstream request.
            upstream_request = httpx.Request(
                method=request.method,
                url=url,
                params=request.query_params.multi_items(),
                headers=headers,
                content=await request.body(),
            )

            upstream_response = await self.client.send(
                upstream_request,
                stream=True,
            )

        except httpx.TimeoutException:
            return JSONResponse(
                {"detail": "Upstream timeout"},
                status_code=504,
            )

        except httpx.RequestError:
            return JSONResponse(
                {"detail": "Service unavailable"},
                status_code=502,
            )

        try:
            # Читаем исходные байты, без автоматической
            # распаковки Content-Encoding.
            body = b"".join([chunk async for chunk in upstream_response.aiter_raw()])

            response_headers = {
                key: value
                for key, value in upstream_response.headers.items()
                if key.lower() not in self.BLOCKED_RESPONSE_HEADERS and key.lower() != "set-cookie"
            }

            result = Response(
                content=body,
                status_code=upstream_response.status_code,
                headers=response_headers,
            )

            if forward_cookies:
                for cookie in upstream_response.headers.get_list("set-cookie"):
                    result.raw_headers.append((b"set-cookie", cookie.encode("latin-1")))

            return result

        except httpx.TimeoutException:
            return JSONResponse(
                {"detail": "Upstream timeout"},
                status_code=504,
            )

        except httpx.RequestError:
            return JSONResponse(
                {"detail": "Service unavailable"},
                status_code=502,
            )

        finally:
            await upstream_response.aclose()
