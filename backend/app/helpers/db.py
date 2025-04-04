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

"""Database module for initializing MongoDB and Redis clients."""

import os
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis  # type: ignore

# Read environment variables or use defaults
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/mcp_app")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Initialize async MongoDB client
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["mcp_app"]

users_coll = db["users"]
tokens_coll = db["tokens"]
schemas_coll = db["entity_schemas"]
entities_coll = db["entities"]
permissions_coll = db["permissions"]  # added permissions collection
auth_codes_coll = db["auth_codes"]
conversations_coll = db["conversations"]

users_coll.create_index("username", unique=True)
tokens_coll.create_index("token", unique=True)
tokens_coll.create_index("user_id")
schemas_coll.create_index("type", unique=True)
entities_coll.create_index("type")
permissions_coll.create_index("user_id", unique=True)  # added index for permissions
conversations_coll.create_index("user_id")

# Initialize async Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


async def populate_db() -> None:
    """Populate the DB with default Person schema if missing."""
    doc = await schemas_coll.find_one({"type": "Person"})
    if not doc:
        await schemas_coll.insert_one(
            {
                "type": "Person",
                "schema": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "title": "Person",
                    "type": "object",
                    "properties": {
                        "firstName": {
                            "type": "string",
                            "description": "The person's first name.",
                        },
                        "lastName": {
                            "type": "string",
                            "description": "The person's last name.",
                        },
                        "email": {
                            "type": "string",
                            "description": "The person's email address.",
                            "format": "email",
                        },
                    },
                    "required": ["firstName", "lastName"],
                    "additionalProperties": False,
                },
            }
        )
