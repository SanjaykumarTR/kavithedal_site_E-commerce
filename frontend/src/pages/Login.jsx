import { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import api from "../api/axios";

export default function Login() {
  const { language } = useContext(LanguageContext);
  const navigate = useNavigate();

  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!form.email || !form.password) {
      setError(language === "en" ? "Please fill in all fields." : "அனைத்து புலங்களையும் நிரப்பவும்.");
      return;
    }
    if (isRegister && !form.name) {
      setError(language === "en" ? "Please enter your name." : "உங்கள் பெயரை உள்ளிடவும்.");
      return;
    }
    setLoading(true);
    try {
      let res;
      if (isRegister) {
        // Registration
        const registerData = {
          username: form.name || form.email.split('@')[0],
          email: form.email,
          password: form.password,
          confirm_password: form.password
        };
        res = await api.post("/api/register/", registerData);
        
        const data = res.data;
        
        if (data.status === "REGISTRATION_SUCCESS") {
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          localStorage.setItem("auth_user", JSON.stringify({ email: data.user.email, role: data.user.role }));
          navigate(data.redirect || "/user-dashboard");
          return;
        } else {
          // Handle other statuses
          setError(data.message || (language === "en" ? "Registration failed" : "பதிவு தோல்வியடைந்தது"));
          return;
        }
      } else {
        // Login
        res = await api.post("/api/login/", {
          email: form.email,
          password: form.password,
        });
        
        const data = res.data;

        // Handle any status - redirect based on role
        if (data.access_token) {
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token || data.access_token);
          localStorage.setItem("auth_user", JSON.stringify({ email: form.email, role: data.role || 'user' }));
          
          // Redirect based on role
          if (data.role === 'superadmin' || data.role === 'admin') {
            navigate("/admin/dashboard");
          } else {
            navigate("/user-dashboard");
          }
          return;
        }
        
        // Handle USER_LOGIN_SUCCESS
        if (data.status === "USER_LOGIN_SUCCESS") {
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          localStorage.setItem("auth_user", JSON.stringify({ email: form.email, role: data.role }));
          localStorage.setItem("admin_user", JSON.stringify({ email: form.email, role: data.role }));
          navigate(data.redirect || "/user-dashboard");
          return;
        }
        
        // Handle ADMIN_OTP_REQUIRED — redirect to OTP verification page
        if (data.status === "ADMIN_OTP_REQUIRED") {
          localStorage.setItem("pending_admin_id", data.admin_id);
          localStorage.setItem("pending_admin_email", form.email);
          navigate(data.redirect || "/verify-otp");
          return;
        }
      }
      
    } catch (err) {
      console.error('Login/Register error:', err);
      console.error('Error response:', err.response?.data);
      let msg;
      if (!err.response) {
        // Network error or CORS — server unreachable
        msg = language === "en"
          ? "Cannot connect to server. Please try again."
          : "சேவையகத்துடன் இணைக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.";
      } else {
        const d = err.response.data;
        msg =
          d?.detail ||
          d?.message ||
          d?.non_field_errors?.[0] ||
          d?.email?.[0] ||
          d?.password?.[0] ||
          d?.username?.[0] ||
          (language === "en" ? "Invalid credentials. Please try again." : "தவறான நற்சான்றிதழ்கள். மீண்டும் முயற்சிக்கவும்.");
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Floating Decorations */}
      <div className="login-decoration login-decoration-1">
        <div className="floating-circle"></div>
      </div>
      <div className="login-decoration login-decoration-2">
        <span className="floating-star">✦</span>
      </div>
      <div className="login-decoration login-decoration-3">
        <div className="floating-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>

      <div className="login-card">
        <div className="login-card-glow"></div>
        
        <h2 className="login-title">
          {isRegister
            ? language === "en" ? "Create Account" : "கணக்கை உருவாக்கு"
            : language === "en" ? "Login" : "உள்நுழை"}
        </h2>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          {isRegister && (
            <div className="input-group">
              <input
                type="text"
                name="name"
                placeholder={language === "en" ? "Full Name" : "முழு பெயர்"}
                value={form.name}
                onChange={handleChange}
                className="modern-input"
              />
            </div>
          )}
          <div className="input-group">
            <input
              type="email"
              name="email"
              placeholder={language === "en" ? "Email" : "மின்னஞ்சல்"}
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
              className="modern-input"
            />
          </div>
          <div className="input-group">
            <input
              type="password"
              name="password"
              placeholder={language === "en" ? "Password" : "கடவுச்சொல்"}
              value={form.password}
              onChange={handleChange}
              autoComplete="current-password"
              className="modern-input"
            />
          </div>
          
          <button type="submit" disabled={loading} className="modern-btn">
            {loading
              ? (language === "en" ? "Please wait..." : "காத்திருக்கவும்...")
              : isRegister
                ? language === "en" ? "Register" : "பதிவு செய்"
                : language === "en" ? "Login" : "உள்நுழை"}
          </button>
        </form>

        <p className="toggle-auth">
          {isRegister ? (
            <>
              {language === "en" ? "Already have an account? " : "ஏற்கனவே கணக்கு உள்ளதா? "}
              <span className="toggle-link login-link" onClick={() => setIsRegister(!isRegister)}>
                {language === "en" ? "Login" : "உள்நுழை"}
              </span>
            </>
          ) : (
            <>
              {language === "en" ? "Don't have an account? " : "கணக்கு இல்லையா? "}
              <span className="toggle-link register-link" onClick={() => setIsRegister(!isRegister)}>
                {language === "en" ? "Register" : "பதிவு செய்"}
              </span>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
