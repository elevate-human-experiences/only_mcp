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

import openai
import falcon
import traceback


# New Falcon resource wrapping chat_endpoint
class ChatResource:
    """Falcon resource for handling chat requests."""

    async def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle POST request for chat completions."""
        try:
            # Read and parse the request body into ChatRequest
            data = await req.get_media()
            try:
                # remove fields that have a None value
                data = {k: v for k, v in data.items() if v is not None}
                response = openai.chat.completions.create(**data)
                if response.choices:
                    result = response.choices[0].message
                else:
                    raise falcon.HTTPInternalServerError(
                        description="No response from OpenAI"
                    )
            except openai.APIError as e:
                traceback.print_exc()
                raise falcon.HTTPInternalServerError(description=str(e))
            except Exception as e:
                traceback.print_exc()
                raise falcon.HTTPInternalServerError(
                    description=f"An unexpected error occurred: {str(e)}"
                )
            resp.media = result.model_dump()
        except Exception as e:
            traceback.print_exc()
            raise falcon.HTTPInternalServerError(description=str(e))
