# MIT License
#
# Copyright (c) 2025 elevate-human-experiences
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Application entry point for the Falcon ASGI app."""

import falcon.asgi
from auth import (
    AuthMiddleware,
    RegisterResource,
    LoginResource,
    LogoutResource,
    MeResource,
)
from resources import (
    EntitiesResource,
    SchemasResource,
    OneEntityResource,
    OneSchemaResource,
)
from falcon import Request, Response, media
from pydantic import ValidationError
import json
import traceback
from functools import partial
from typing import Any
import nest_asyncio
from core.setup_logging import setup_logger
from core.encoder import CustomJsonEncoder, CustomJsonDecoder
from oauth import OAuthAuthorizeResource, OAuthTokenResource, WellKnownOAuthResource
from mcp import MCPResource
from chat import ChatResource

# Patch the event loop with nest_asyncio
nest_asyncio.apply()
# Create a custom logger
logger = setup_logger(__name__)


async def handle_validation_error(
    req: Request, resp: Response, exception: ValidationError, params: Any
) -> None:
    """Handle Pydantic ValidationError exceptions."""
    # Optionally log the exception details
    logger.error(f"Validation error: {exception}")

    # Set the HTTP status code to 422 Unprocessable Entity
    resp.status = falcon.HTTP_422

    # Prepare a detailed error response
    resp.media = {
        "title": "Unprocessable Entity",
        "description": "The request contains invalid data.",
        "errors": exception.errors(),
    }


async def custom_handle_uncaught_exception(
    req: Request, resp: Response, exception: Exception, _: Any
) -> None:
    """Handle uncaught exceptions."""
    traceback.print_exc()
    resp.status = falcon.HTTP_500
    resp.media = f"{exception}"


# Create an async Falcon app instance
app = falcon.asgi.App(middleware=[AuthMiddleware()], cors_enable=True)
app.add_error_handler(ValidationError, handle_validation_error)
app.add_error_handler(Exception, custom_handle_uncaught_exception)

# JSON Handler for the config
json_handler = media.JSONHandler(
    dumps=partial(json.dumps, cls=CustomJsonEncoder, sort_keys=True),
    loads=partial(json.loads, cls=CustomJsonDecoder),
)
extra_handlers = {
    "application/json": json_handler,
}
app.req_options.media_handlers.update(extra_handlers)
app.resp_options.media_handlers.update(extra_handlers)

# Public auth endpoints
app.add_route("/api/auth/register", RegisterResource())
app.add_route("/api/auth/login", LoginResource())
app.add_route("/api/auth/logout", LogoutResource())
app.add_route("/api/auth/me", MeResource())

# Protected RESTful endpoints
app.add_route("/api/schemas", SchemasResource())
app.add_route("/api/schemas/{schema_id}", OneSchemaResource())
app.add_route("/api/schemas/{schema_id}/entities", EntitiesResource())
app.add_route("/api/schemas/{schema_id}/entities/{entity_id}", OneEntityResource())

# Auth MCP endpoints
app.add_route("/.well-known/oauth-authorization-server", WellKnownOAuthResource())
app.add_route("/api/oauth/authorize", OAuthAuthorizeResource())
app.add_route("/api/oauth/token", OAuthTokenResource())

# MCP endpoint
app.add_route("/api/mcp", MCPResource())

# Chat endpoint
app.add_route("/api/chat", ChatResource())

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
