import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { EntitiesPage } from "@/pages/EntitiesPage";
import { Chat } from "@/components/Chat";
import { OAuthLoginPage } from "@/pages/OAuthLoginPage";

function App() {
  const [user, setUser] = useState<string | null>(null);

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
          const data = await res.json();
          setUser(data.user_id);
        } else {
          setUser(null);
        }
      } catch (err) {
        setUser(null);
      }
    }
    checkAuth();
  }, []);

  const handleLogin = (newUser: string) => {
    setUser(newUser);
  };

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    setUser(null);
  };

  return (
    <BrowserRouter>
      <nav className="p-4 border-b mb-4 flex gap-4">
        <Link to="/">Home</Link>
        {user ? (
          <>
            <Link to="/entities">Entities</Link>
            <button onClick={handleLogout}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </nav>
      <Routes>
        <Route
          path="/"
          element={
            <div className="p-4">
              Personal DB
              <div className="w-full">
                <Chat />
              </div>
            </div>
          }
        />
        <Route
          path="/login"
          element={user ? <Navigate to="/entities" /> : <LoginPage />}
        />
        <Route
          path="/register"
          element={user ? <Navigate to="/entities" /> : <RegisterPage />}
        />
        <Route
          path="/entities"
          element={
            user ? <EntitiesPage token={user} /> : <Navigate to="/login" />
          }
        />
        {/* New OAuth routes */}
        <Route
          path="/oauth/login"
          element={
            user ? (
              <Navigate to="/entities" />
            ) : (
              <OAuthLoginPage onLoginOAuth={handleLogin} />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
