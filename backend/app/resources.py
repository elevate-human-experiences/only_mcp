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

from falcon import HTTPBadRequest, HTTPNotFound, Request, Response, HTTP_201
from helpers.entities import EntityHelper
from helpers.entity_schemas import SchemaHelper
from helpers.db import populate_db


class EntitiesResource:
    """Resource for entity CRUDL operations."""

    async def on_get(self, req: Request, resp: Response, schema_id: str) -> None:
        """Handle GET request for entities."""
        user_id = req.context.user_id
        entity_id = req.get_param("_id")
        if entity_id:
            data = await EntityHelper.get(user_id, schema_id, entity_id)
            if data is None:
                raise HTTPNotFound()
            resp.media = {"id": entity_id, "type": schema_id, "data": data}
        else:
            entities = await EntityHelper.list(
                user_id=user_id, entity_type=schema_id
            )  # fixed argument name
            resp.media = {"type": schema_id, "entities": entities}

    async def on_post(self, req: Request, resp: Response, schema_id: str) -> None:
        """Handle POST request to create an entity."""
        user_id = req.context.user_id
        body = await req.get_media() or {}
        data = body.get("data")
        if not isinstance(data, dict):
            raise HTTPBadRequest(description="Must provide 'data' (object)")
        try:
            new_id = await EntityHelper.create(user_id, schema_id, data)
        except Exception as e:
            raise HTTPBadRequest(description=str(e))
        resp.status = HTTP_201
        resp.media = {"status": "created", "id": new_id, "type": schema_id}

    async def on_put(self, req: Request, resp: Response, schema_id: str) -> None:
        """Handle PUT request to update an entity."""
        user_id = req.context.user_id
        body = await req.get_media() or {}
        entity_id = body.get("_id")
        new_data = body.get("data")
        if not (entity_id and isinstance(new_data, dict)):
            raise HTTPBadRequest(description="Must provide '_id' and 'data'")
        try:
            updated = await EntityHelper.update(user_id, entity_id, schema_id, new_data)
        except Exception as e:
            raise HTTPBadRequest(description=str(e))
        if not updated:
            raise HTTPNotFound(description="Entity not found or not owned by user")
        resp.media = {"status": "updated", "_id": entity_id, "type": schema_id}

    async def on_delete(self, req: Request, resp: Response, schema_id: str) -> None:
        """Handle DELETE request to remove an entity."""
        user_id = req.context.user_id
        entity_id = req.get_param("_id")
        if not entity_id:
            raise HTTPBadRequest(description="Query param '_id' is required")
        deleted = await EntityHelper.delete(user_id, schema_id, entity_id)
        if not deleted:
            raise HTTPNotFound(description="Entity not found or not owned by user")
        resp.media = {"status": "deleted", "_id": entity_id, "type": schema_id}


class SchemasResource:
    """Resource for schema CRUDL operations."""

    async def on_get(self, req: Request, resp: Response) -> None:
        """Handle GET request to fetch one or all schemas."""
        _ = req.context.user_id
        schema_type = req.get_param("type")
        await populate_db()
        if schema_type:
            schema_data = await SchemaHelper.get(schema_type)
            if schema_data is None:
                raise HTTPNotFound(description=f"Schema '{schema_type}' not found")
            resp.media = {"type": schema_type, "schema": schema_data}
        else:
            schemas = await SchemaHelper.list()
            resp.media = {"schemas": schemas}

    async def on_post(self, req: Request, resp: Response) -> None:
        """Handle POST request to create a new schema."""
        await populate_db()
        # Create new schema
        user_id = req.context.user_id
        body = await req.get_media() or {}
        schema_type = body.get("type")
        schema_obj = body.get("schema")

        if not schema_type or not isinstance(schema_obj, dict):
            raise HTTPBadRequest(
                description="Must provide 'type' (string) and 'schema' (object)"
            )

        try:
            new_id = await SchemaHelper.create(user_id, schema_type, schema_obj)
        except Exception as e:
            raise HTTPBadRequest(description=str(e))

        resp.status = HTTP_201
        resp.media = {
            "status": "created",
            "schema_type": schema_type,
            "id": str(new_id),
        }

    async def on_put(self, req: Request, resp: Response) -> None:
        """Handle PUT request to update an existing schema."""
        await populate_db()

        # Update an existing schema
        _ = req.context.user_id
        body = await req.get_media() or {}
        schema_type = body.get("type")
        schema_obj = body.get("schema")

        if not schema_type or not isinstance(schema_obj, dict):
            raise HTTPBadRequest(description="Must provide 'type' and updated 'schema'")

        try:
            updated = await SchemaHelper.update(schema_type, schema_obj)
        except Exception as e:
            raise HTTPBadRequest(description=f"Invalid JSON Schema: {str(e)}")

        if not updated:
            raise HTTPNotFound(description=f"Schema '{schema_type}' not found")

        resp.media = {"status": "updated", "schema_type": schema_type}

    async def on_delete(self, req: Request, resp: Response) -> None:
        """Handle DELETE request to remove a schema."""
        # Delete schema
        _ = req.context.user_id
        schema_type = req.get_param("type")
        if not schema_type:
            raise HTTPBadRequest(description="Query param 'type' is required")

        deleted = await SchemaHelper.delete(schema_type)
        if not deleted:
            raise HTTPNotFound(description=f"Schema '{schema_type}' not found")

        resp.media = {"status": "deleted", "schema_type": schema_type}


class OneEntityResource:
    """Resource for single entity CRUD operations using RESTful URL."""

    async def on_get(
        self, req: Request, resp: Response, schema_id: str, entity_id: str
    ) -> None:
        """Handle GET request for a single entity using RESTful URL."""
        user_id = req.context.user_id
        data = await EntityHelper.get(user_id, schema_id, entity_id)
        if data is None:
            raise HTTPNotFound(description="Entity not found")
        resp.media = {"id": entity_id, "type": schema_id, "data": data}

    async def on_put(
        self, req: Request, resp: Response, schema_id: str, entity_id: str
    ) -> None:
        """Handle PUT request to update a single entity using RESTful URL."""
        user_id = req.context.user_id
        body = await req.get_media() or {}
        new_data = body.get("data")
        if not isinstance(new_data, dict):
            raise HTTPBadRequest(description="Must provide 'data' as an object")
        try:
            updated = await EntityHelper.update(user_id, entity_id, schema_id, new_data)
        except Exception as e:
            raise HTTPBadRequest(description=str(e))
        if not updated:
            raise HTTPNotFound(description="Entity not found or not owned by user")
        resp.media = {"status": "updated", "id": entity_id, "type": schema_id}

    async def on_delete(
        self, req: Request, resp: Response, schema_id: str, entity_id: str
    ) -> None:
        """Handle DELETE request to remove a single entity using RESTful URL."""
        user_id = req.context.user_id
        deleted = await EntityHelper.delete(user_id, schema_id, entity_id)
        if not deleted:
            raise HTTPNotFound(description="Entity not found or not owned by user")
        resp.media = {"status": "deleted", "id": entity_id, "type": schema_id}


class OneSchemaResource:
    """Resource for single schema CRUD operations using RESTful URL."""

    async def on_get(self, req: Request, resp: Response, schema_id: str) -> None:
        """Handle GET request for a single schema using RESTful URL."""
        await populate_db()
        schema_data = await SchemaHelper.get(schema_id)
        if schema_data is None:
            raise HTTPNotFound(description=f"Schema '{schema_id}' not found")
        resp.media = {"type": schema_id, "schema": schema_data}

    async def on_put(self, req: Request, resp: Response, schema_id: str) -> None:
        """Handle PUT request to update a single schema using RESTful URL."""
        await populate_db()
        body = await req.get_media() or {}
        schema_obj = body.get("schema")
        if not isinstance(schema_obj, dict):
            raise HTTPBadRequest(description="Must provide 'schema' as an object")
        try:
            updated = await SchemaHelper.update(schema_id, schema_obj)
        except Exception as e:
            raise HTTPBadRequest(description=f"Invalid JSON Schema: {str(e)}")
        if not updated:
            raise HTTPNotFound(description=f"Schema '{schema_id}' not found")
        resp.media = {"status": "updated", "type": schema_id}

    async def on_delete(self, req: Request, resp: Response, schema_id: str) -> None:
        """Handle DELETE request to remove a single schema using RESTful URL."""
        deleted = await SchemaHelper.delete(schema_id)
        if not deleted:
            raise HTTPNotFound(description=f"Schema '{schema_id}' not found")
        resp.media = {"status": "deleted", "type": schema_id}
