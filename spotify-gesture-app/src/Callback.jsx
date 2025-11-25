// src/Callback.jsx
import React, { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";

const Callback = () => {
  const [searchParams] = useSearchParams();
  console.log("🧠 Callback component mounted");
  useEffect(() => {
    const code = searchParams.get("code");

    if (code) {
      axios
        .post("http://127.0.0.1:5000/exchange_token", { code })
        .then(() => {
          console.log("✅ Token sent to backend");
        })
        .catch((err) => {
          console.error("❌ Token exchange failed", err);
        });
    }
  }, [searchParams]);

  return (
    <div style={{ textAlign: "center", marginTop: "20vh" }}>
      <h2>✅ You're now logged in with Spotify!</h2>
      <p>You may now close this tab.</p>
    </div>
  );
};

export default Callback;