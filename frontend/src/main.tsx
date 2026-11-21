import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { initKeycloak } from "./auth/keycloak";
import "./styles.css";

const root = ReactDOM.createRoot(document.getElementById("root")!);

initKeycloak()
  .then((authenticated) => {
    if (authenticated) {
      root.render(
        <React.StrictMode>
          <App />
        </React.StrictMode>
      );
    }
  })
  .catch((err) => {
    root.render(
      <div className="container">
        <div className="error">
          Failed to initialise Keycloak authentication: {String(err)}
        </div>
      </div>
    );
  });