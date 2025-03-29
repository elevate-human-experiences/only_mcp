import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { EntitiesPage } from "@/pages/EntitiesPage";

function App() {
  // We'll store the JWT token in state.
  // In a real app, you might store in localStorage or a Context.
  const [token, setToken] = useState<string | null>(null);

  const handleLogin = (newToken: string) => {
    setToken(newToken);
    // localStorage.setItem('jwt', newToken); // if you want to persist across refresh
  };

  const handleLogout = () => {
    setToken(null);
    // localStorage.removeItem('jwt');
  };

  return (
    <BrowserRouter>
      <nav className="p-4 border-b mb-4 flex gap-4">
        <Link to="/">Home</Link>
        {token ? (
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
          element={<div className="p-4">Welcome to MCP Frontend</div>}
        />
        <Route
          path="/login"
          element={
            token ? (
              <Navigate to="/entities" />
            ) : (
              <LoginPage onLogin={handleLogin} />
            )
          }
        />
        <Route
          path="/register"
          element={token ? <Navigate to="/entities" /> : <RegisterPage />}
        />
        <Route
          path="/entities"
          element={
            token ? <EntitiesPage token={token} /> : <Navigate to="/login" />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
