"""Module for handling JSON-RPC MCP backend operations."""
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

from typing import Any
import traceback
import falcon
from helpers.entities import EntityHelper
from helpers.entity_schemas import SchemaHelper
from helpers.json_rpc_schemas import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
)


class MCPResource:
    """Handler for JSON-RPC requests."""

    async def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle JSON-RPC POST requests."""
        user_id = req.context.user_id
        # Parse the raw JSON body
        try:
            request_data = await req.get_media()
            print(f"Request data: {user_id} - {request_data}")
        except Exception as e:
            # If JSON parsing fails, respond with -32700 (Parse error)
            error = JSONRPCError(code=-32700, message="Parse error", data=str(e))
            error_resp = JSONRPCResponse(jsonrpc="2.0", id=None, error=error)
            resp.media = error_resp.dict()
            return

        # Support batch or single-request
        if isinstance(request_data, list):
            requests = request_data
        else:
            requests = [request_data]

        responses = []
        for req_item in requests:
            response = await self._process_single_request(req_item, user_id)
            if response is not None:
                responses.append(response)

        # New: Check Accept header to handle text/event-stream
        accept = req.get_header("Accept") or ""
        if "text/event-stream" in accept:
            import json  # Ensure json is imported

            resp.content_type = "text/event-stream"
            if isinstance(request_data, list):
                events = (
                    "\n".join(f"data: {json.dumps(response)}" for response in responses)
                    + "\n\n"
                )
            else:
                events = (
                    "data: " + json.dumps(responses[0] if responses else {}) + "\n\n"
                )
            resp.text = events
        else:
            if isinstance(request_data, list):
                resp.media = responses
            else:
                resp.media = responses[0] if responses else None

    async def _process_single_request(
        self, req_item: dict[str, Any], user_id: str
    ) -> Any:
        """Process a single JSON-RPC request item."""
        try:
            req_obj = JSONRPCRequest.model_validate(req_item)
        except Exception as e:
            traceback.print_exc()
            # Invalid JSON-RPC request structure
            error = JSONRPCError(code=-32600, message="Invalid Request", data=str(e))
            req_id = req_item.get("id") if isinstance(req_item, dict) else None
            error_resp = JSONRPCResponse(jsonrpc="2.0", id=req_id, error=error)
            return error_resp.dict()

        # If this is a notification (no id), process without forming a response
        if req_obj.id is None:
            try:
                await self._dispatch_request(req_obj, user_id=user_id)
            except Exception:
                traceback.print_exc()
            return None

        # Process request and return a response
        try:
            result_payload = await self._dispatch_request(req_obj, user_id=user_id)
            success_resp = JSONRPCResponse(
                jsonrpc="2.0", id=req_obj.id, result=result_payload
            )
            return success_resp.model_dump()
        except falcon.HTTPError as http_e:
            traceback.print_exc()
            error = JSONRPCError(
                code=-32601, message=str(http_e), data=http_e.to_dict()
            )
            error_resp = JSONRPCResponse(jsonrpc="2.0", id=req_obj.id, error=error)
            return error_resp.model_dump()
        except Exception as e:
            traceback.print_exc()
            error = JSONRPCError(code=-32603, message="Internal error", data=str(e))
            error_resp = JSONRPCResponse(jsonrpc="2.0", id=req_obj.id, error=error)
            return error_resp.model_dump()

    async def _dispatch_request(self, req_obj: JSONRPCRequest, user_id: str) -> Any:
        """Dispatch a JSON-RPC request to the appropriate helper."""
        method = req_obj.method
        params = req_obj.params or {}
        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "entities-list",
                        "description": 'List entities in the Personal DB, optionally filtering by entity type (e.g. Person). Example: Call with { "entity_type": "Person" } to list all persons.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_type": {
                                    "type": "string",
                                    "description": "Optional entity type filter",
                                }
                            },
                        },
                    },
                    {
                        "name": "entities-read",
                        "description": 'Read entity details by entity_type and id in the Personal DB. Example: Call with { "entity_type": "Person", "id": "abc" } to retrieve a specific person entity.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_type": {
                                    "type": "string",
                                    "description": "Entity type",
                                },
                                "id": {"type": "string", "description": "Entity id"},
                            },
                            "required": ["entity_type", "id"],
                        },
                    },
                    {
                        "name": "entities-create",
                        "description": 'Create an entity with provided attributes in the Personal DB. Example: Call with { "entity_type": "Person", "attributes": { "name": "John Doe", "age": 30 } } to create a new person entity.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_type": {
                                    "type": "string",
                                    "description": "Entity type",
                                },
                                "attributes": {
                                    "type": "object",
                                    "description": "Attributes for the entity",
                                },
                            },
                            "required": ["entity_type", "attributes"],
                        },
                    },
                    {
                        "name": "entities-update",
                        "description": 'Update an entity with new attributes in the Personal DB. Example: Call with { "id": "abc", "entity_type": "Person", "attributes": { "age": 31 } } to update the age of a person entity.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "Entity id"},
                                "entity_type": {
                                    "type": "string",
                                    "description": "Entity type",
                                },
                                "attributes": {
                                    "type": "object",
                                    "description": "New attributes for the entity",
                                },
                            },
                            "required": ["id", "entity_type", "attributes"],
                        },
                    },
                    {
                        "name": "entities-delete",
                        "description": 'Delete an entity by entity_type and id in the Personal DB. Example: Call with { "entity_type": "Person", "id": "abc" } to delete a specific person entity.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_type": {
                                    "type": "string",
                                    "description": "Entity type",
                                },
                                "id": {"type": "string", "description": "Entity id"},
                            },
                            "required": ["entity_type", "id"],
                        },
                    },
                    {
                        "name": "schemas-list",
                        "description": "List schemas and different entity types in the Personal DB. Example: Simply call this function with no parameters to list all available schemas.",
                        "parameters": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "schemas-read",
                        "description": 'Read a schema by schema_type in the Personal DB. Example: Call with { "schema_type": "Person" } to retrieve the schema for Person entities.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "schema_type": {
                                    "type": "string",
                                    "description": "Schema type",
                                }
                            },
                            "required": ["schema_type"],
                        },
                    },
                    {
                        "name": "schemas-create",
                        "description": 'Create a new schema in the Personal DB. Example: Call with { "schema_type": "Person", "schema_obj": { "fields": { "name": "string", "age": "number" } } } to create a new Person schema.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "schema_type": {
                                    "type": "string",
                                    "description": "Schema type",
                                },
                                "schema_obj": {
                                    "type": "object",
                                    "description": "Schema object",
                                },
                            },
                            "required": ["schema_type", "schema_obj"],
                        },
                    },
                    {
                        "name": "schemas-update",
                        "description": 'Update an existing schema in the Personal DB. Example: Call with { "schema_type": "Person", "schema_obj": { "fields": { "name": "string", "age": "number", "email": "string" } } } to update the Person schema with a new email field.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "schema_type": {
                                    "type": "string",
                                    "description": "Schema type",
                                },
                                "schema_obj": {
                                    "type": "object",
                                    "description": "Schema object",
                                },
                            },
                            "required": ["schema_type", "schema_obj"],
                        },
                    },
                    {
                        "name": "schemas-delete",
                        "description": 'Delete a schema in the Personal DB. Example: Call with { "schema_type": "Person" } to delete the Person schema.',
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "schema_type": {
                                    "type": "string",
                                    "description": "Schema type",
                                }
                            },
                            "required": ["schema_type"],
                        },
                    },
                ]
            }
        elif method == "tools/call":
            # "tool" param must be provided: e.g. "entities/list", "schemas/read", etc.
            tool_name = params.get("name")
            if not tool_name:
                raise falcon.HTTPBadRequest(
                    description="Missing 'tool' in params for tools/call"
                )

            # All other arguments for that tool go under "args"
            tool_args = params.get("arguments", {})
            return await self._call_tool(tool_name, tool_args, user_id=user_id)

        # Unrecognized top-level method
        raise falcon.HTTPBadRequest(description=f"Method '{method}' not found")

    async def _call_tool(
        self, tool_name: str, args: dict[str, Any], user_id: str
    ) -> Any:
        """Dispatch tool call with provided arguments."""
        if tool_name.startswith("entities-"):
            action = tool_name.split("-", 1)[1]
            if action == "list":
                # List entities (optional: pass an entity_type)
                result = await EntityHelper.list(
                    user_id=user_id, entity_type=args.get("entity_type", "")
                )
                return {"entities": result, "nextCursor": None}
            elif action == "read":
                entity = await EntityHelper.get(
                    user_id=user_id,
                    entity_type=args["entity_type"],
                    entity_id=args["id"],
                )
                return {"entity": entity}

            elif action == "create":
                new_entity = await EntityHelper.create(
                    user_id=user_id,
                    entity_type=args["entity_type"],
                    data=args["attributes"],
                )
                return {"entity": new_entity}

            elif action == "update":
                updated = await EntityHelper.update(
                    user_id=user_id,
                    entity_id=args["id"],
                    entity_type=args["entity_type"],
                    new_data=args["attributes"],
                )
                return {"entity": updated}

            elif action == "delete":
                success = await EntityHelper.delete(
                    user_id=user_id,
                    entity_type=args["entity_type"],
                    entity_id=args["id"],
                )
                return {"success": success}

            else:
                # Unknown entity method
                raise falcon.HTTPBadRequest(description=f"Unknown tool '{tool_name}'")

        elif tool_name.startswith("schemas-"):
            action = tool_name.split("-", 1)[1]
            if action == "list":
                result = await SchemaHelper.list()
                return {"schemas": result, "nextCursor": None}

            elif action == "read":
                result = await SchemaHelper.get(schema_type=args["schema_type"])
                return {"schema": result}

            elif action == "create":
                new_schema = await SchemaHelper.create(
                    user_id=user_id,
                    schema_type=args["schema_type"],
                    schema_obj=args["schema_obj"],
                )
                return {"schema": new_schema}
            elif action == "update":
                updated_schema = await SchemaHelper.update(
                    schema_type=args["schema_type"],
                    schema_obj=args["schema_obj"],
                )
                return {"schema": updated_schema}

            elif action == "delete":
                success = await SchemaHelper.delete(schema_type=args["schema_type"])
                return {"success": success}
            else:
                raise falcon.HTTPBadRequest(description=f"Unknown tool '{tool_name}'")
        else:
            raise falcon.HTTPBadRequest(description=f"Unknown tool '{tool_name}'")
