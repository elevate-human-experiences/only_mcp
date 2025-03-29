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
import bcrypt
import jwt
import datetime
from uuid import uuid4
import falcon
from falcon import HTTPUnauthorized, HTTPBadRequest, HTTPConflict, Request, Response
from db import users_coll, tokens_coll
from typing import Any

# Load JWT secret from environment
JWT_SECRET = os.environ.get("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGO = "HS256"
JWT_EXP_SECONDS = 3600 * 24  # 1 day expiry for access tokens


def hash_password(plain_password: str) -> Any:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt)


def verify_password(plain_password: str, password_hash: bytes) -> Any:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash)


class AuthMiddleware:
    """Middleware to authenticate requests via JWT."""

    async def process_request(self, req: Request, resp: Response) -> Response:
        """Validate the JWT from the Authorization header and attach user ID to the context."""
        # Allow public endpoints (registration, login) without auth
        if req.path.startswith("/api/auth/"):
            return

        auth_header = req.get_header("Authorization")
        if not auth_header:
            raise HTTPUnauthorized(description="Missing Authorization header")

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
        token_doc = tokens_coll.find_one({"token": token})
        if not token_doc:
            raise HTTPUnauthorized(
                description="Token is not recognized (possibly revoked or invalid)"
            )

        # Attach user info to request context
        req.context.user_id = payload["sub"]  # store user ID as string
        # We could store entire payload if needed: req.context.auth_payload = payload


class RegisterResource:
    """Resource to register a new user."""

    async def on_post(self, req: Request, resp: Response) -> Response:
        """Handle a POST request to register a user."""
        body = await req.get_media()
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            raise HTTPBadRequest(description="Username and password are required")

        # Check if user already exists
        existing_user = await users_coll.find_one({"username": username})
        if existing_user:
            raise HTTPConflict(description="Username already taken")

        # Hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)

        # Create user in DB
        user_doc = {
            "_id": str(uuid4()),
            "username": username,
            "password_hash": password_hash,
            "created_at": datetime.datetime.utcnow(),
        }
        result = await users_coll.insert_one(user_doc)

        resp.status = falcon.HTTP_201
        resp.media = {"status": "registered", "_id": str(result.inserted_id)}


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
        user = await users_coll.find_one({"username": username})
        if not user:
            raise HTTPUnauthorized(description="Invalid credentials")

        # Check password
        if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"]):
            raise HTTPUnauthorized(description="Invalid credentials")

        # Generate JWT token
        now = datetime.datetime.utcnow()
        exp = now + datetime.timedelta(seconds=JWT_EXP_SECONDS)
        payload = {
            "sub": str(user["_id"]),
            "iat": now,
            "exp": exp,
            "username": username,
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

        # Store token in DB for potential revocation
        await tokens_coll.find_one_and_update(
            {"_id": user["_id"]},
            update={"$set": {"token": token, "expires_at": exp}},
            upsert=True,
        )

        resp.media = {"access_token": token}
