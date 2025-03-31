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

import base64
import hashlib
import falcon
from helpers.db import auth_codes_coll
from helpers.users import Users
from helpers.tokens import Tokens
import secrets
import string
import datetime


class WellKnownOAuthResource:
    async def on_get(self, _: falcon.Request, resp: falcon.Response) -> None:
        """
        Serve the OAuth 2.0 Authorization Server Metadata document (RFC 8414).
        Adjust the URLs to match your actual domain/ports and any additional
        endpoints (e.g., introspection, revocation, registration).
        """
        # In production, use HTTPS and your real domain
        issuer_url = "https://localhost:4096"

        resp.media = {
            "issuer": issuer_url,
            "authorization_endpoint": f"{issuer_url}/api/oauth/authorize",
            "token_endpoint": f"{issuer_url}/api/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256", "plain"],
        }


class OAuthAuthorizeResource:
    """Handles the authorization request to issue an 'authorization code'."""

    async def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle GET request for OAuth authorization."""
        # 1. Check if the user is logged in
        user_id = getattr(req.context, "user_id", None)
        if not user_id:
            raise falcon.HTTPUnauthorized(
                description="User not authenticated. Please log in first before using oauth flow."
            )

        # 2. Parse parameters
        response_type = req.get_param("response_type")
        client_id = req.get_param("client_id")
        redirect_uri = req.get_param("redirect_uri")
        code_challenge = req.get_param("code_challenge")
        code_challenge_method = req.get_param("code_challenge_method") or "S256"
        state = req.get_param("state")
        scope = req.get_param("scope") or ""  # store or validate as needed

        # Quick helper to do "error=...&state=..." redirection
        def redirect_with_error(error: str, description: str) -> None:
            location = f"{redirect_uri}?error={error}&error_description={description}"
            if state:
                location += f"&state={state}"
            resp.status = falcon.HTTP_302
            resp.set_header("Location", location)
            return

        # 3. Basic checks and client validation
        if response_type != "code":
            return redirect_with_error(
                "unsupported_response_type", "Only 'code' is supported"
            )

        # If you have a client registry, verify client_id is valid and redirect_uri matches
        # For illustration, do a naive check here:
        if not client_id or not redirect_uri or not code_challenge:
            return redirect_with_error(
                "invalid_request", "Missing client_id, redirect_uri, or code_challenge"
            )

        # Optionally enforce only S256 for PKCE:
        if code_challenge_method != "S256":
            return redirect_with_error("invalid_request", "Only S256 PKCE is supported")

        # 4. Generate the authorization code
        auth_code = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
        )

        # 5. Store the auth code doc
        now = datetime.datetime.utcnow()
        doc = {
            "_id": auth_code,
            "user_id": user_id,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "scope": scope,
            "created_at": now,
            "expires_at": now + datetime.timedelta(minutes=10),
            "used": False,
        }
        await auth_codes_coll.insert_one(doc)

        # 6. Redirect with the authorization code (and state if present)
        redirect_location = f"{redirect_uri}?code={auth_code}"
        if state:
            redirect_location += f"&state={state}"

        resp.status = falcon.HTTP_302  # Found / Redirect
        resp.set_header("Location", redirect_location)


class OAuthTokenResource:
    async def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle POST request for token exchange."""
        form_data = await req.get_media()

        grant_type = form_data.get("grant_type")
        code = form_data.get("code")
        redirect_uri = form_data.get("redirect_uri")
        client_id = form_data.get("client_id")
        code_verifier = form_data.get("code_verifier")

        if grant_type != "authorization_code":
            resp.status = falcon.HTTP_400
            resp.media = {
                "error": "unsupported_grant_type",
                "error_description": "Must be authorization_code",
            }
            return

        if not code or not redirect_uri or not client_id or not code_verifier:
            resp.status = falcon.HTTP_400
            resp.media = {
                "error": "invalid_request",
                "error_description": "Missing required parameters",
            }
            return

        code_doc = await auth_codes_coll.find_one({"_id": code})
        if not code_doc:
            resp.status = falcon.HTTP_400
            resp.media = {
                "error": "invalid_grant",
                "error_description": "Authorization code not found",
            }
            return

        # check used/expired
        if code_doc.get("used"):
            resp.status = falcon.HTTP_400
            resp.media = {
                "error": "invalid_grant",
                "error_description": "Authorization code already used.",
            }
            return

        if code_doc["expires_at"] < datetime.datetime.utcnow():
            resp.status = falcon.HTTP_400
            resp.media = {
                "error": "invalid_grant",
                "error_description": "Authorization code expired.",
            }
            return

        if code_doc["client_id"] != client_id:
            resp.status = falcon.HTTP_400
            resp.media = {
                "error": "invalid_request",
                "error_description": "Invalid client_id for this code.",
            }
            return

        if code_doc["redirect_uri"] != redirect_uri:
            resp.status = falcon.HTTP_400
            resp.media = {
                "error": "invalid_request",
                "error_description": "Mismatched redirect_uri.",
            }
            return

        # PKCE check
        if code_doc["code_challenge_method"] == "S256":
            hashed = hashlib.sha256(code_verifier.encode("utf-8")).digest()
            computed_challenge = (
                base64.urlsafe_b64encode(hashed).rstrip(b"=").decode("utf-8")
            )

            if computed_challenge != code_doc["code_challenge"]:
                resp.status = falcon.HTTP_400
                resp.media = {
                    "error": "invalid_grant",
                    "error_description": "PKCE validation failed.",
                }
                return
        else:
            # If you want to disallow 'plain', you could error out here
            if code_verifier != code_doc["code_challenge"]:
                resp.status = falcon.HTTP_400
                resp.media = {
                    "error": "invalid_grant",
                    "error_description": "PKCE (plain) validation failed.",
                }
                return

        # All good, generate token
        user_id = code_doc["user_id"]
        user = await Users.get_user_by_id(user_id)
        if not user:
            resp.status = falcon.HTTP_400
            resp.media = {
                "error": "invalid_grant",
                "error_description": "User not found.",
            }
            return

        access_token = await Tokens.get_token(user_id)

        # Mark code used
        await auth_codes_coll.update_one({"_id": code}, {"$set": {"used": True}})

        resp.media = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 86400,  # 1 day, adjust as needed
        }
