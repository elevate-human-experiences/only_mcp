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

"""Auth module for handling user authentication."""

import os
import jwt
from falcon import (
    HTTPUnauthorized,
    HTTPBadRequest,
    HTTPConflict,
    Request,
    Response,
    HTTP_201,
)
from helpers.users import Users
from helpers.tokens import Tokens
from helpers.permissions import Permissions

# Load JWT secret from environment
JWT_SECRET = os.environ.get("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGO = "HS256"
JWT_EXP_SECONDS = 3600 * 24  # 1 day expiry for access tokens


class AuthMiddleware:
    """Middleware to authenticate requests via JWT."""

    async def process_request(self, req: Request, resp: Response) -> Response:
        """Validate the JWT from the Authorization header and attach user ID to the context."""
        # Allow public endpoints (registration, login) without auth

        if req.path == "/sse":
            return

        if not req.path.startswith("/api"):
            # For UI
            return

        if req.path in ["/api/auth/register", "/api/auth/login"]:
            return

        if req.path == "/api/chat":
            # For chat
            return

        # New: try to get token from session cookie first
        token = req.cookies.get("session")
        if token:
            # token obtained from session cookie
            pass
        else:
            auth_header = req.get_header("Authorization")
            if not auth_header:
                raise HTTPUnauthorized(
                    description="Missing Authorization header or session cookie"
                )
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                raise HTTPUnauthorized(
                    description="Invalid Authorization header format. Use 'Bearer <token>'"
                )
            token = parts[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        except jwt.ExpiredSignatureError:
            raise HTTPUnauthorized(description="Token expired, please log in again")
        except jwt.InvalidTokenError:
            raise HTTPUnauthorized(description="Invalid token")

        # Optional: Check DB if token is active (revocation, etc.)
        token_doc = await Tokens.get_token(token)
        if not token_doc:
            raise HTTPUnauthorized(
                description="Token is not recognized (possibly revoked or invalid)"
            )

        # Attach user info to request context
        req.context.user_id = payload["sub"]  # store user ID as string


class RegisterResource:
    """Resource to register a new user."""

    async def on_post(self, req: Request, resp: Response) -> Response:
        """Handle a POST request to register a user."""
        body = await req.get_media()
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            raise HTTPBadRequest(description="Username and password are required")

        # Delegate user creation to users.py
        try:
            user_doc = await Users.create_user(username, password)
        except Exception as e:
            raise HTTPConflict(description=str(e))

        resp.status = HTTP_201
        resp.media = {"status": "registered", "_id": user_doc["_id"]}


class LoginResource:
    """Resource to log in a user and issue a JWT token."""

    async def on_post(self, req: Request, resp: Response) -> Response:
        """Handle a POST request to authenticate a user and generate a JWT token."""
        body = await req.get_media()
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            raise HTTPBadRequest(description="Username and password are required")

        # Find user
        user = await Users.get_user_by_username(username)
        if not user:
            raise HTTPUnauthorized(description="Invalid credentials")

        # Check password
        if not Users.verify_password(password, user["password_hash"]):
            raise HTTPUnauthorized(description="Invalid credentials")

        # Delegate token generation and storage to tokens.py
        token = await Tokens.generate_and_store_token(user)
        print(f"Insert token payload: {token}")
        # Set session cookie with token
        resp.set_cookie(
            "session",
            token,
            secure=True,
            http_only=True,
            max_age=JWT_EXP_SECONDS,
            path="/",
            same_site="Lax",
        )

        # Return confirmation without token in the body
        resp.media = {"status": "logged_in"}


class LogoutResource:
    """Resource to log out a user by clearing the session cookie."""

    async def on_post(self, req: Request, resp: Response) -> None:
        """Log out the user by clearing the session cookie."""
        # Clear the session cookie with supported parameters, including correct path
        resp.unset_cookie(
            "session",
            path="/",
            samesite="Lax",
        )
        resp.media = {"status": "logged_out"}


class MeResource:
    """Resource to check if the user is logged in."""

    async def on_get(self, req: Request, resp: Response) -> None:
        """Return the login status of the current user."""
        # Check if user is attached by the AuthMiddleware
        user_id = getattr(req.context, "user_id", None)
        if not user_id:
            raise HTTPUnauthorized(description="Not logged in")
        resp.media = {"status": "logged_in", "user_id": user_id}


class PermissionsResource:
    """Resource to handle CRUDL operations on user permissions."""

    async def on_get(self, req: Request, resp: Response, user_id: str) -> None:
        """Retrieve permissions for a specified user."""
        # Retrieve permissions based on user_id provided in the URL
        permissions = await Permissions.get(user_id)
        if not permissions:
            raise HTTPBadRequest(description="Permissions not found for the user")
        resp.media = permissions

    async def on_patch(self, req: Request, resp: Response, user_id: str) -> None:
        """Update permissions for a specified user."""
        # Get update data from request payload
        update_data = await req.get_media()
        # Only allow updating permissions fields (crudl_entities, crudl_schemas)
        allowed_fields = {"crudl_entities", "crudl_schemas"}
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not update_fields:
            raise HTTPBadRequest(description="No valid permissions fields to update")

        result = await Permissions.update(user_id, update_fields)
        if not result:
            raise HTTPBadRequest(description="Permissions not found or update failed")
        resp.media = result
