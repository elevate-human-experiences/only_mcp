import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

interface OAuthLoginPageProps {
  onLoginOAuth: (token: string) => void;
}

export function OAuthLoginPage({ onLoginOAuth }: OAuthLoginPageProps) {
  const [error, setError] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const code = searchParams.get("code");

  useEffect(() => {
    if (!code) return;

    const storedVerifier = localStorage.getItem("pkce_code_verifier");
    if (!storedVerifier) {
      setError("Missing PKCE code verifier.");
      return;
    }

    const exchangeToken = async () => {
      try {
        const res = await fetch("/api/oauth/token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            grant_type: "authorization_code",
            code,
            code_verifier: storedVerifier,
            client_id: "FRONTEND_4096",
            redirect_uri: window.location.origin + "/oauth/login",
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(
            errData.error_description || "OAuth token retrieval failed.",
          );
        }

        const data = await res.json();
        if (!data.access_token) {
          throw new Error("No access_token in token response.");
        }
        sessionStorage.setItem("oauth_token", data.access_token);
        localStorage.removeItem("pkce_code_verifier");
        onLoginOAuth(data.access_token);
        window.location.href = "/";
      } catch (err: any) {
        setError(err.message);
      }
    };

    exchangeToken();
  }, [code, onLoginOAuth, navigate]);

  return (
    <div className="max-w-md mx-auto p-4">
      <h1 className="text-xl font-bold mb-4">OAuth Login</h1>
      {error && <div className="text-red-500 text-sm mb-2">{error}</div>}
      {code ? (
        <p>Processing OAuth login...</p>
      ) : (
        <p>Waiting for OAuth redirect...</p>
      )}
    </div>
  );
}
