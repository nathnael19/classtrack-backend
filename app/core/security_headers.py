from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds baseline security headers to HTTP responses.
    (Does not replace deeper application-layer security controls.)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Clickjacking protection
        response.headers.setdefault("X-Frame-Options", "DENY")

        # MIME sniffing protection
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Reduce information leakage via referrer
        response.headers.setdefault("Referrer-Policy", "no-referrer")

        # Basic CSP for the served frontend.
        # Allow OSM tiles used by Leaflet.
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "connect-src 'self' ws: wss: http: https:; "
            "font-src 'self' data:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )

        # HSTS only makes sense over HTTPS.
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains; preload",
            )

        return response

