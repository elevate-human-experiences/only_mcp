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

from typing import Dict, Any, Union, Optional
from pydantic import BaseModel, Field


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 Request (notifications when id is None)."""

    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    # Make 'id' truly optional for notifications:
    id: Optional[Union[int, str]] = Field(
        default=None,
        description="Request ID. If omitted or null, this is considered a notification.",
    )


class JSONRPCError(BaseModel):
    """JSON-RPC Error structure."""

    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 Response (one of result or error must be present)."""

    jsonrpc: str = "2.0"
    id: Union[int, str, None]
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None

    class Config:
        validate_assignment = True

    def __init__(self, **data: Any) -> None:
        """Initialize and enforce result/error exclusivity."""
        super().__init__(**data)
        # Enforce JSON-RPC result/error exclusivity
        if (self.result is None) == (self.error is None):
            raise ValueError("Response must have exactly one of 'result' or 'error'.")
