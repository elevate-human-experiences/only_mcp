"""Module for token operations."""  # Added module docstring
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

import os
import jwt
import datetime
from helpers.db import tokens_coll
from typing import Any, Dict

JWT_SECRET = os.environ.get("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGO = "HS256"
JWT_EXP_SECONDS = 3600 * 24  # 1 day expiry


class Tokens:
    """Class for token operations."""  # Added single line class docstring

    @staticmethod
    async def generate_and_store_token(user: Dict[str, Any]) -> str:
        """Generate JWT token and store it in the DB."""  # Added method docstring
        now = datetime.datetime.utcnow()
        exp = now + datetime.timedelta(seconds=JWT_EXP_SECONDS)
        payload = {
            "sub": str(user["_id"]),
            "iat": now,
            "exp": exp,
            "username": user["username"],
        }
        token: str = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
        await tokens_coll.find_one_and_update(
            {"_id": user["_id"]},
            {"$set": {"token": token, "expires_at": exp}},
            upsert=True,
        )
        return token

    @staticmethod
    async def get_token(token: str) -> Any:
        """Retrieve token details from the DB."""  # Added method docstring
        return await tokens_coll.find_one({"token": token})
