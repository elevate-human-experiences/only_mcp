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

"""Schemas helper functions."""

import json
import datetime
import jsonschema
from helpers.db import schemas_coll, redis_client
from typing import Any, Dict


class SchemaHelper:
    @staticmethod
    async def get(schema_type: str) -> Any:
        """Get a schema by type."""
        cache_key = f"schema:{schema_type}"
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return json.loads(cached)
        doc = await schemas_coll.find_one({"type": schema_type})
        if not doc:
            return None
        schema_data = doc["schema"]
        await redis_client.set(cache_key, json.dumps(schema_data))
        return schema_data

    @staticmethod
    async def list() -> Any:
        """List all schemas."""
        cursor = schemas_coll.find({})
        docs = await cursor.to_list(length=None)
        return [{"type": d["type"], "schema": d["schema"]} for d in docs]

    @staticmethod
    async def create(user_id: str, schema_type: str, schema_obj: Dict[str, Any]) -> str:
        """Create a new schema."""
        existing = await schemas_coll.find_one({"type": schema_type})
        if existing:
            raise Exception(f"Schema for type '{schema_type}' already exists")
        jsonschema.Draft202012Validator.check_schema(schema_obj)
        doc = {
            "type": schema_type,
            "schema": schema_obj,
            "created_by": user_id,
            "created_at": datetime.datetime.utcnow(),
        }
        result = await schemas_coll.insert_one(doc)
        await redis_client.set(f"schema:{schema_type}", json.dumps(schema_obj))
        return str(result.inserted_id)

    @staticmethod
    async def update(schema_type: str, schema_obj: Dict[str, Any]) -> bool:
        """Update an existing schema."""
        jsonschema.Draft202012Validator.check_schema(schema_obj)
        res = await schemas_coll.update_one(
            {"type": schema_type},
            {"$set": {"schema": schema_obj, "updated_at": datetime.datetime.utcnow()}},
        )
        if res.matched_count == 0:
            return False
        await redis_client.set(f"schema:{schema_type}", json.dumps(schema_obj))
        return True

    @staticmethod
    async def delete(schema_type: str) -> bool:
        """Delete a schema by type."""
        res = await schemas_coll.delete_one({"type": schema_type})
        if res.deleted_count == 0:
            return False
        await redis_client.delete(f"schema:{schema_type}")
        return True
