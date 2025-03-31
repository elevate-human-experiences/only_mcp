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

"""Entities helper functions."""

from typing import Any, Dict, Optional
import json
import datetime
import jsonschema
from uuid import uuid4
from helpers.db import entities_coll, schemas_coll, redis_client


class EntityHelper:
    @staticmethod
    async def get(user_id: str, entity_type: str, entity_id: str) -> Optional[Any]:
        """Retrieve an entity by ID and type for a user."""
        cache_key = f"entity:{entity_type}:{entity_id}"
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return json.loads(cached)
        doc = await entities_coll.find_one(
            {"_id": entity_id, "type": entity_type, "created_by": user_id}
        )
        if not doc:
            return None
        data = doc["data"]
        await redis_client.set(cache_key, json.dumps(data))
        return data

    @staticmethod
    async def list(user_id: str, entity_type: str) -> Any:
        """List entities for a given user and type."""
        cache_key = f"entity_list:{user_id}:{entity_type}"
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return json.loads(cached)
        cursor = entities_coll.find({"type": entity_type, "created_by": user_id})
        docs = await cursor.to_list(length=None)
        entities = [{"id": str(doc["_id"]), "data": doc["data"]} for doc in docs]
        await redis_client.set(cache_key, json.dumps(entities))
        return entities

    @staticmethod
    async def create(user_id: str, entity_type: str, data: Dict[str, Any]) -> str:
        """Create a new entity for a user with given type and data."""
        schema_doc = await schemas_coll.find_one({"type": entity_type})
        if not schema_doc:
            raise Exception(f"No schema found for type '{entity_type}'")
        jsonschema.validate(instance=data, schema=schema_doc["schema"])

        new_id = str(uuid4())
        doc = {
            "_id": new_id,
            "type": entity_type,
            "data": data,
            "created_by": user_id,
            "created_at": datetime.datetime.utcnow(),
        }
        await entities_coll.insert_one(doc)
        await redis_client.set(f"entity:{entity_type}:{new_id}", json.dumps(data))
        await redis_client.delete(f"entity_list:{entity_type}")
        return new_id

    @staticmethod
    async def update(
        user_id: str, entity_id: str, entity_type: str, new_data: Dict[str, Any]
    ) -> bool:
        """Update an existing entity's data for a user."""
        schema_doc = await schemas_coll.find_one({"type": entity_type})
        if not schema_doc:
            raise Exception(f"No schema found for type '{entity_type}'")
        jsonschema.validate(instance=new_data, schema=schema_doc["schema"])

        res = await entities_coll.update_one(
            {"_id": entity_id, "type": entity_type, "created_by": user_id},
            {"$set": {"data": new_data, "updated_at": datetime.datetime.utcnow()}},
        )
        if res.matched_count == 0:
            return False
        await redis_client.set(
            f"entity:{entity_type}:{entity_id}", json.dumps(new_data)
        )
        await redis_client.delete(f"entity_list:{entity_type}")
        return True

    @staticmethod
    async def delete(user_id: str, entity_type: str, entity_id: str) -> bool:
        """Delete an entity by ID for a user and type."""
        res = await entities_coll.delete_one(
            {"_id": entity_id, "type": entity_type, "created_by": user_id}
        )
        if res.deleted_count == 0:
            return False
        await redis_client.delete(f"entity:{entity_type}:{entity_id}")
        await redis_client.delete(f"entity_list:{entity_type}")
        return True
