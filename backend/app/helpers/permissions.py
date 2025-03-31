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

"""Permissions helper functions for managing user permissions in a web application."""

from helpers.db import permissions_coll
from typing import Any, Dict


class Permissions:
    @staticmethod
    async def get(user_id: str) -> Any:
        """Retrieve permissions for a given user."""
        return await permissions_coll.find_one({"user_id": user_id})

    @staticmethod
    async def update(user_id: str, update_fields: Dict[str, Any]) -> Any:
        """Update permissions for a given user."""
        return await permissions_coll.find_one_and_update(
            {"user_id": user_id}, {"$set": update_fields}, return_document=True
        )

    @staticmethod
    async def create_default(user_id: str) -> Dict[str, Any]:
        """Create default permissions for a given user."""
        permissions = {
            "user_id": user_id,
            "entities": {"create": True, "read": True, "update": True, "delete": True},
            "schemas": {
                "create": False,
                "read": True,
                "update": False,
                "delete": False,
            },
        }
        result = await permissions_coll.insert_one(permissions)
        permissions["_id"] = str(result.inserted_id)
        return permissions
