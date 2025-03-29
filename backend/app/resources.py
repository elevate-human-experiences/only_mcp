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

"""Resources module for handling entity and schema CRUD operations."""

import json
import falcon
import datetime
import jsonschema
from falcon import HTTPBadRequest, HTTPNotFound, Request, Response
from db import entities_coll, schemas_coll, redis_client
from uuid import uuid4


class EntityResource:
    """Resource for entity CRUDL operations."""

    async def on_get(self, req: Request, resp: Response) -> Response:
        """Handle GET request to read or list entities."""
        _ = req.context.user_id  # from AuthMiddleware
        entity_type = req.get_param("type")
        entity_id = req.get_param("_id")

        if not entity_type:
            raise HTTPBadRequest(description="Missing 'type' param")

        if entity_id:
            # Read single entity
            cache_key = f"entity:{entity_type}:{entity_id}"
            cached_entity = await redis_client.get(cache_key)
            if cached_entity is not None:
                data = json.loads(cached_entity)
            else:
                doc = await entities_coll.find_one(
                    {
                        "_id": entity_id,
                        "type": entity_type,
                        # optionally: "created_by": ObjectId(user_id) if each user sees only their own
                    }
                )
                if not doc:
                    raise HTTPNotFound()
                data = doc["data"]
                # Update cache
                await redis_client.set(cache_key, json.dumps(data))

            resp.media = {"id": entity_id, "type": entity_type, "data": data}
        else:
            # List all entities of given type
            cache_key = f"entity_list:{entity_type}"
            cached_list = await redis_client.get(cache_key)
            if cached_list is not None:
                entities = json.loads(cached_list)
            else:
                # Possibly filter by user if multi-tenant
                cursor = entities_coll.find({"type": entity_type})
                entities = []
                docs = await cursor.to_list(length=None)
                for doc in docs:
                    entities.append({"id": str(doc["_id"]), "data": doc["data"]})
                await redis_client.set(cache_key, json.dumps(entities))

            resp.media = {"type": entity_type, "entities": entities}

    async def on_post(self, req: Request, resp: Response) -> Response:
        """Handle POST request to create a new entity."""
        # Create new entity
        user_id = req.context.user_id
        body = await req.get_media() or {}
        entity_type = body.get("type")
        data = body.get("data")

        if not entity_type or not isinstance(data, dict):
            raise HTTPBadRequest(description="Must provide 'type' and 'data' (object)")

        # Validate data against the stored JSON schema for that type
        schema_doc = await schemas_coll.find_one({"type": entity_type})
        if not schema_doc:
            raise HTTPBadRequest(
                description=f"No schema found for type '{entity_type}'"
            )

        try:
            jsonschema.validate(instance=data, schema=schema_doc["schema"])
        except jsonschema.ValidationError as e:
            raise HTTPBadRequest(description=f"Schema validation error: {e.message}")

        # Insert into DB
        doc = {
            "_id": str(uuid4()),
            "type": entity_type,
            "data": data,
            "created_by": user_id,  # track ownership
            "created_at": datetime.datetime.utcnow(),
        }
        result = await entities_coll.insert_one(doc)
        new_id = str(result.inserted_id)

        # Write-through cache: store entity data
        await redis_client.set(f"entity:{entity_type}:{new_id}", json.dumps(data))
        # Invalidate list cache
        await redis_client.delete(f"entity_list:{entity_type}")

        resp.status = falcon.HTTP_201
        resp.media = {"status": "created", "id": new_id, "type": entity_type}

    async def on_put(self, req: Request, resp: Response) -> Response:
        """Handle PUT request to update an existing entity."""
        # Update existing entity
        user_id = req.context.user_id
        body = await req.get_media() or {}
        entity_id = body.get("_id")
        entity_type = body.get("type")
        new_data = body.get("data")

        if not (entity_id and entity_type and isinstance(new_data, dict)):
            raise HTTPBadRequest(description="Must provide '_id', 'type', and 'data'")

        # Validate new data
        schema_doc = await schemas_coll.find_one({"type": entity_type})
        if not schema_doc:
            raise HTTPBadRequest(
                description=f"No schema found for type '{entity_type}'"
            )

        try:
            jsonschema.validate(instance=new_data, schema=schema_doc["schema"])
        except jsonschema.ValidationError as e:
            raise HTTPBadRequest(description=f"Schema validation error: {e.message}")

        # Update in DB (check ownership if needed)
        res = await entities_coll.update_one(
            {
                "_id": entity_id,
                "type": entity_type,
                "created_by": user_id,
            },
            {"$set": {"data": new_data, "updated_at": datetime.datetime.utcnow()}},
        )

        if res.matched_count == 0:
            raise HTTPNotFound(description="Entity not found or not owned by user")

        # Update cache
        await redis_client.set(
            f"entity:{entity_type}:{entity_id}", json.dumps(new_data)
        )
        await redis_client.delete(f"entity_list:{entity_type}")

        resp.media = {"status": "updated", "_id": entity_id, "type": entity_type}

    async def on_delete(self, req: Request, resp: Response) -> Response:
        """Handle DELETE request to remove an entity."""
        # Delete an entity
        user_id = req.context.user_id
        entity_type = req.get_param("type")
        entity_id = req.get_param("_id")

        if not (entity_type and entity_id):
            raise HTTPBadRequest(
                description="Query params 'type' and '_id' are required"
            )

        res = await entities_coll.delete_one(
            {
                "_id": entity_id,
                "type": entity_type,
                "created_by": user_id,
            }
        )

        if res.deleted_count == 0:
            raise HTTPNotFound(description="Entity not found or not owned by user")

        # Remove from cache
        await redis_client.delete(f"entity:{entity_type}:{entity_id}")
        await redis_client.delete(f"entity_list:{entity_type}")

        resp.media = {"status": "deleted", "_id": entity_id, "type": entity_type}


class SchemaResource:
    """Resource for schema CRUDL operations."""

    async def on_get(self, req: Request, resp: Response) -> Response:
        """Handle GET request to fetch one or all schemas."""
        _ = req.context.user_id
        schema_type = req.get_param("type")
        if schema_type:
            # Read single schema
            cache_key = f"schema:{schema_type}"
            cached = await redis_client.get(cache_key)
            if cached is not None:
                schema_data = json.loads(cached)
            else:
                doc = await schemas_coll.find_one({"type": schema_type})
                if not doc:
                    raise HTTPNotFound(description=f"Schema '{schema_type}' not found")
                schema_data = doc["schema"]
                await redis_client.set(cache_key, json.dumps(schema_data))
            resp.media = {"type": schema_type, "schema": schema_data}
        else:
            # List all schemas
            # Could cache a list of schema types
            # For simplicity, fetch from DB each time or use a separate key
            cursor = schemas_coll.find({})
            docs = await cursor.to_list(length=None)
            schemas = []
            for d in docs:
                schemas.append({"type": d["type"], "schema": d["schema"]})
            resp.media = {"schemas": schemas}

    async def on_post(self, req: Request, resp: Response) -> Response:
        """Handle POST request to create a new schema."""
        # Create new schema
        user_id = req.context.user_id
        body = await req.get_media() or {}
        schema_type = body.get("type")
        schema_obj = body.get("schema")

        if not schema_type or not isinstance(schema_obj, dict):
            raise HTTPBadRequest(
                description="Must provide 'type' (string) and 'schema' (object)"
            )

        # Check if schema already exists
        existing = await schemas_coll.find_one({"type": schema_type})
        if existing:
            raise HTTPBadRequest(
                description=f"Schema for type '{schema_type}' already exists"
            )

        # Optionally validate the schema itself is a valid JSON Schema
        try:
            jsonschema.Draft202012Validator.check_schema(schema_obj)
        except jsonschema.SchemaError as e:
            raise HTTPBadRequest(description=f"Invalid JSON Schema: {str(e)}")

        doc = {
            "type": schema_type,
            "schema": schema_obj,
            "created_by": user_id,
            "created_at": datetime.datetime.utcnow(),
        }
        result = await schemas_coll.insert_one(doc)
        # Write-through cache
        await redis_client.set(f"schema:{schema_type}", json.dumps(schema_obj))

        resp.status = falcon.HTTP_201
        resp.media = {
            "status": "created",
            "schema_type": schema_type,
            "id": str(result.inserted_id),
        }

    async def on_put(self, req: Request, resp: Response) -> Response:
        """Handle PUT request to update an existing schema."""
        # Update an existing schema
        _ = req.context.user_id
        body = await req.get_media() or {}
        schema_type = body.get("type")
        schema_obj = body.get("schema")

        if not schema_type or not isinstance(schema_obj, dict):
            raise HTTPBadRequest(description="Must provide 'type' and updated 'schema'")

        # Validate schema
        try:
            jsonschema.Draft202012Validator.check_schema(schema_obj)
        except jsonschema.SchemaError as e:
            raise HTTPBadRequest(description=f"Invalid JSON Schema: {str(e)}")

        res = await schemas_coll.update_one(
            {"type": schema_type},
            {"$set": {"schema": schema_obj, "updated_at": datetime.datetime.utcnow()}},
        )

        if res.matched_count == 0:
            raise HTTPNotFound(description=f"Schema '{schema_type}' not found")

        # Update cache
        await redis_client.set(f"schema:{schema_type}", json.dumps(schema_obj))

        resp.media = {"status": "updated", "schema_type": schema_type}

    async def on_delete(self, req: Request, resp: Response) -> Response:
        """Handle DELETE request to remove a schema."""
        # Delete schema
        _ = req.context.user_id
        schema_type = req.get_param("type")
        if not schema_type:
            raise HTTPBadRequest(description="Query param 'type' is required")

        res = await schemas_coll.delete_one({"type": schema_type})
        if res.deleted_count == 0:
            raise HTTPNotFound(description=f"Schema '{schema_type}' not found")

        # Remove from cache
        await redis_client.delete(f"schema:{schema_type}")

        # Potentially also remove or orphan existing entities of that type
        # or require that no entities exist for that type before deleting
        # For now, do nothing extra.

        resp.media = {"status": "deleted", "schema_type": schema_type}
