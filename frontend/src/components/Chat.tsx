import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";

// JSON-RPC 2.0 request structure
interface JSONRPCRequest {
  jsonrpc: "2.0";
  id: string | number | null;
  method: string;
  params?: Record<string, any>;
}

// JSON-RPC 2.0 response
interface JSONRPCResponse {
  jsonrpc: "2.0";
  id: string | number | null;
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

// Define the Tool type
interface Tool {
  name: string;
  description: string;
}

export function Chat() {
  const [conversation, setConversation] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isConnectedToMCP, setIsConnectedToMCP] = useState<boolean>(false); // New flag
  const [tools, setTools] = useState<Tool[]>([]);

  const [codeVerifier, setCodeVerifier] = useState<string | null>(null);

  const conversationContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (conversationContainerRef.current) {
      conversationContainerRef.current.scrollTop =
        conversationContainerRef.current.scrollHeight;
    }
  }, [conversation]);

  useEffect(() => {
    if (isConnectedToMCP) {
      (async () => {
        try {
          const res = await sendMCPRequest("tools/list", {});
          if (res?.result?.tools && Array.isArray(res.result.tools)) {
            setTools(res.result.tools);
            console.log("Available tools:", res.result.tools);
          } else {
            console.warn("Unexpected tool list response format", res);
          }
        } catch (err) {
          console.error("Failed to fetch tools from MCP:", err);
        }
      })();
    }
  }, [isConnectedToMCP]);

  // Handle potential OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");
    const storedVerifier = localStorage.getItem("pkce_code_verifier");
    if (code && storedVerifier) {
      // Clear from URL
      window.history.replaceState({}, "", window.location.pathname);
      // Exchange code for token
      exchangeCodeForToken(code, storedVerifier);
    }
  }, []);

  // Check sessionStorage for existing token
  useEffect(() => {
    const sessionToken = sessionStorage.getItem("oauth_token");
    if (sessionToken) {
      setAccessToken(sessionToken);
      setIsConnectedToMCP(true);
    }
  }, []);

  const exchangeCodeForToken = async (code: string, verifier: string) => {
    try {
      // We fetch the well-known data again to get the token_endpoint
      const metaRes = await fetch("/.well-known/oauth-authorization-server");
      if (!metaRes.ok) {
        throw new Error(
          "Failed to fetch OAuth well-known config for token exchange",
        );
      }
      const meta = await metaRes.json();
      const tokenEndpoint = meta.token_endpoint;

      const tokenRes = await fetch(tokenEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          grant_type: "authorization_code",
          code,
          code_verifier: verifier,
          client_id: "FRONTEND_4096",
          redirect_uri: window.location.origin + "/oauth/callback",
        }),
      });

      if (!tokenRes.ok) {
        throw new Error("Token exchange failed");
      }

      const tokenData = await tokenRes.json();
      if (!tokenData.access_token) {
        throw new Error("No access_token in token response");
      }

      // Store token
      setAccessToken(tokenData.access_token);
      sessionStorage.setItem("oauth_token", tokenData.access_token);
      setIsConnectedToMCP(true);
      localStorage.removeItem("pkce_code_verifier");
    } catch (error: any) {
      console.error("Code exchange error:", error);
    }
  };

  const requestIdRef = useRef<number>(0);

  // Send a JSON-RPC request to /api/mcp
  const sendMCPRequest = async (
    method: string,
    params: Record<string, any>,
    isNotification = false,
  ): Promise<JSONRPCResponse | null> => {
    requestIdRef.current += 1;
    const requestId = isNotification ? null : requestIdRef.current;

    const requestBody: JSONRPCRequest = {
      jsonrpc: "2.0",
      method,
      id: requestId,
      params,
    };

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (accessToken) {
        headers["Authorization"] = `Bearer ${accessToken}`;
      }

      const res = await fetch("/api/mcp", {
        method: "POST",
        headers,
        body: JSON.stringify(requestBody),
      });

      // If it was a notification, no response is expected.
      if (isNotification) {
        if (!res.ok) {
          throw new Error(`Notification request failed, status ${res.status}`);
        }
        return null;
      }

      // If 401, do the OAuth flow
      if (res.status === 401) {
        await handleOAuthFlow();
        return null;
      }

      if (!res.ok) {
        throw new Error(`Request failed with status ${res.status}`);
      }

      const data: JSONRPCResponse = await res.json();
      return data;
    } catch (error) {
      console.error("MCP request error:", error);
      throw error;
    }
  };

  // Called on 401 to redirect user for OAuth
  const handleOAuthFlow = async () => {
    try {
      const metaRes = await fetch("/.well-known/oauth-authorization-server");
      if (!metaRes.ok) {
        throw new Error("Failed to fetch OAuth well-known config");
      }
      const meta = await metaRes.json();
      const authorizationEndpoint = meta.authorization_endpoint;

      const verifier = generateCodeVerifier(64);
      const challenge = await pkceChallengeFromVerifier(verifier);
      localStorage.setItem("pkce_code_verifier", verifier);

      const redirectUri = window.location.origin + "/oauth/login";

      const authUrl = new URL(authorizationEndpoint);
      authUrl.searchParams.set("response_type", "code");
      authUrl.searchParams.set("client_id", "FRONTEND_4096");
      authUrl.searchParams.set("redirect_uri", redirectUri);
      authUrl.searchParams.set("scope", "openid profile");
      authUrl.searchParams.set("code_challenge", challenge);
      authUrl.searchParams.set("code_challenge_method", "S256");

      window.location.href = authUrl.toString();
    } catch (error) {
      console.error("OAuth flow error:", error);
    }
  };

  // PKCE helpers
  function generateCodeVerifier(length: number) {
    const possible =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
    let text = "";
    for (let i = 0; i < length; i++) {
      text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
  }

  async function pkceChallengeFromVerifier(verifier: string) {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await window.crypto.subtle.digest("SHA-256", data);
    return base64UrlEncode(new Uint8Array(digest));
  }

  function base64UrlEncode(buffer: Uint8Array) {
    let str = btoa(String.fromCharCode(...buffer));
    return str.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  /**
   *  callTool: Invoke a tool via MCP
   *  @param name The tool's name
   *  @param args The JSON arguments to pass to the tool
   */
  const callTool = async (name: string, args: any): Promise<string> => {
    try {
      // "tools.invoke" is the standard method for calling tools in MCP
      const response = await sendMCPRequest("tools/call", {
        name,
        arguments: args,
      });
      console.log("Tool call response:", response);
      if (response?.error) {
        throw new Error(`Tool call error: ${response.error.message}`);
      }
      // Return the tool's response or a fallback
      return response?.result ?? "No result from tool";
    } catch (err) {
      console.error("callTool error:", err);
      throw err;
    }
  };

  // =============== Chat usage example ===============
  const sendMessage = async () => {
    if (!input.trim()) return;

    // Step 1: Add user message to conversation
    const userMessage = { role: "user", content: input };
    const newConversation = [...conversation, userMessage];
    setConversation(newConversation);
    setInput("");

    // Step 2: Construct payload
    const payload: any = {
      model: "gpt-4o-mini",
      messages: newConversation,
    };

    if (tools.length > 0) {
      payload.tools = tools.map((tool) => ({
        type: "function",
        function: tool,
      }));
    }

    try {
      // Step 3: Send user message to backend
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Chat API request failed, status ${res.status}`);
      }

      const responseMessage = await res.json();
      // Step 4: Check if model is calling a tool
      if (responseMessage.tool_calls) {
        const toolResults = [];
        for (const call of responseMessage.tool_calls) {
          // Now call your tool via MCP (JSON-RPC)
          const result = await callTool(
            call.function.name,
            JSON.parse(call.function.arguments),
          );
          toolResults.push({
            role: "tool",
            tool_call_id: call.id,
            content: JSON.stringify(result),
          });
        }

        // Step 5: Send tool results back to OpenAI
        const toolPayload = {
          model: "gpt-4o-mini",
          messages: [...newConversation, responseMessage, ...toolResults],
        };

        const secondRes = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(toolPayload),
        });

        if (!secondRes.ok) {
          throw new Error(
            `Tool chain API request failed, status ${secondRes.status}`,
          );
        }

        const finalMessage = await secondRes.json();
        console.log("Final response after tool use:", finalMessage);
        setConversation((prev) => [
          ...prev,
          responseMessage,
          ...toolResults,
          finalMessage,
        ]);
      } else {
        // Normal assistant reply without any tool calls
        setConversation((prev) => [...prev, responseMessage]);
      }
    } catch (error: any) {
      const errorReply = {
        role: "assistant",
        content: `Error: ${error.message}`,
      };
      setConversation((prev) => [...prev, errorReply]);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-4">
      {isConnectedToMCP ? (
        <div className="mb-4 flex justify-end">
          <span className="text-green-600">Connected to MCP Server.</span>
        </div>
      ) : (
        <div className="mb-4 flex justify-between items-center">
          <span className="text-gray-700">
            Using Chat API <b>Without MCP</b>
          </span>
          <Button variant="ghost" onClick={handleOAuthFlow}>
            Connect to MCP Server
          </Button>
        </div>
      )}
      <div
        ref={conversationContainerRef}
        className="mb-4 border p-4 rounded h-80 overflow-y-auto"
      >
        {conversation
          .filter(
            (msg) =>
              msg.role === "user" ||
              (msg.role === "assistant" && !msg.tool_calls),
          )
          .map((msg, index) => (
            <div
              key={index}
              className={`mb-2 ${
                msg.role === "user" ? "text-right" : "text-left"
              }`}
            >
              <p className="px-2 py-1 rounded inline-block bg-gray-100">
                <strong>
                  {msg.role === "user" ? "You" : "Assistant"}:&nbsp;
                </strong>{" "}
                {msg.content}
              </p>
            </div>
          ))}
      </div>

      {/* Display an input for the user message */}
      <div className="flex items-center space-x-2">
        <textarea
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyUp={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              sendMessage();
            }
          }}
          className="flex-1 p-2 border rounded"
        />
        <Button onClick={sendMessage}>Send</Button>
      </div>

      {tools.length > 0 && (
        <div className="mt-5 p-4 bg-gray-100">
          <h3 className="font-bold mb-2">Connected Tools:</h3>
          <ul>
            {tools.map((tool, index) => (
              <li key={index}>
                <strong>{tool.name}</strong>: {tool.description}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
