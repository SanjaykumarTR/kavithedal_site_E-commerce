import { Link } from "react-router-dom";
import { useContext } from "react";
import { LanguageContext } from "../context/LanguageContext";

export default function NotFound() {
  const { language } = useContext(LanguageContext);

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "60vh",
      textAlign: "center",
      padding: "2rem",
    }}>
      <h1 style={{ fontSize: "6rem", margin: 0, color: "#B71C1C" }}>404</h1>
      <h2 style={{ margin: "0.5rem 0 1rem" }}>
        {language === "en" ? "Page Not Found" : "பக்கம் கிடைக்கவில்லை"}
      </h2>
      <p style={{ color: "#666", marginBottom: "2rem" }}>
        {language === "en"
          ? "The page you are looking for does not exist or has been moved."
          : "நீங்கள் தேடும் பக்கம் இல்லை அல்லது நகர்த்தப்பட்டுள்ளது."}
      </p>
      <Link
        to="/"
        style={{
          background: "#B71C1C",
          color: "#fff",
          padding: "0.75rem 2rem",
          borderRadius: "8px",
          textDecoration: "none",
          fontWeight: 600,
        }}
      >
        {language === "en" ? "Go to Home" : "முகப்பிற்கு செல்"}
      </Link>
    </div>
  );
}
