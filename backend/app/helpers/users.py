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

from typing import Dict, Any, cast
import bcrypt
import datetime
from uuid import uuid4
from helpers.db import users_coll
from helpers.permissions import Permissions


class Users:
    @staticmethod
    def hash_password(plain_password: str) -> bytes:
        """Hash plain password using bcrypt."""
        salt = bcrypt.gensalt()
        return cast(bytes, bcrypt.hashpw(plain_password.encode("utf-8"), salt))

    @staticmethod
    def verify_password(plain_password: str, password_hash: bytes) -> bool:
        """Verify plain password against given hashed password."""
        return cast(bool, bcrypt.checkpw(plain_password.encode("utf-8"), password_hash))

    @classmethod
    async def get_user_by_username(cls, username: str) -> Any:
        """Retrieve user document by username."""
        return await users_coll.find_one({"username": username})

    @classmethod
    async def create_user(cls, username: str, password: str) -> Any:
        """Create a new user and set up default permissions."""
        existing = await users_coll.find_one({"username": username})
        if existing:
            raise Exception("Username already taken")
        password_hash = cls.hash_password(password)
        user_doc: Dict[str, Any] = {
            "_id": str(uuid4()),
            "username": username,
            "password_hash": password_hash,
            "created_at": datetime.datetime.utcnow(),
        }
        result = await users_coll.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        await Permissions.create_default(str(user_doc["_id"]))
        return user_doc

    @classmethod
    async def get_user_by_id(cls, user_id: str) -> Any:
        """Retrieve user document by user ID."""
        return await users_coll.find_one({"_id": user_id})
