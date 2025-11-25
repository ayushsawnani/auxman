// src/Login.jsx
const CLIENT_ID = process.env.REACT_APP_SPOTIFY_CLIENT_ID;
const REDIRECT_URI = process.env.REACT_APP_SPOTIFY_REDIRECT_URI;
const SCOPES = process.env.REACT_APP_SPOTIFY_SCOPES;

const Login = () => {
  const loginUrl = `https://accounts.spotify.com/authorize?client_id=${CLIENT_ID}&response_type=code&redirect_uri=${encodeURIComponent(
    REDIRECT_URI
  )}&scope=${encodeURIComponent(SCOPES)}`;

  return (
    <div style={{ textAlign: "center", marginTop: "20vh" }}>
      <h1>Spotify Gesture Controller</h1>
      <a href={loginUrl}>
        <button style={{ padding: "10px 20px", fontSize: "16px" }}>
          Login with Spotify
        </button>
      </a>
    </div>
  );
};

export default Login;