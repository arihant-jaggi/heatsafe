import { BrowserRouter, Routes, Route } from "react-router-dom";
import Shell from "./components/Shell";
import Landing from "./pages/Landing";
import About from "./pages/About";
import HowItWorks from "./pages/HowItWorks";

// IMPORTANT: This imports your existing working route planner.
// We are NOT rewriting it here.
import App from "./App";

export default function RouterApp() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <Shell>
              <Landing />
            </Shell>
          }
        />
        <Route
          path="/about"
          element={
            <Shell>
              <About />
            </Shell>
          }
        />
        <Route
          path="/how"
          element={
            <Shell>
              <HowItWorks />
            </Shell>
          }
        />
        <Route
          path="/app"
          element={
            <Shell>
              <App />
            </Shell>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
