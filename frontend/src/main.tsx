import React from "react";
import ReactDOM from "react-dom/client";
import RouterApp from "./RouterApp";

// Keep these imports so your existing app styles still work
import "./index.css";

// If your map uses Leaflet and you were importing Leaflet CSS before,
// keep it here. It's safe even if already present elsewhere.
import "leaflet/dist/leaflet.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterApp />
  </React.StrictMode>
);
