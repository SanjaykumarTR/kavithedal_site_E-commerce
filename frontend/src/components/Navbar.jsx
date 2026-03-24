import { Link, useNavigate } from "react-router-dom";
import { useState, useContext } from "react";
import { LanguageContext } from "../context/LanguageContext";
import { CartContext } from "../context/CartContext";
import { WishlistContext } from "../context/WishlistContext";
import { useAuth } from "../context/AuthContext";
import logo from "../assects/kavithedal.logo.png";
import "../styles/navbar.css";

export default function Navbar() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [showCategories, setShowCategories] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { language, toggleLanguage } = useContext(LanguageContext);
  const { cartCount } = useContext(CartContext);
  const { wishlistCount } = useContext(WishlistContext);
  const { user, logout, isAdmin } = useAuth();

  const handleLoginClick = () => {
    navigate("/login");
  };

  const handleLogout = () => {
    setShowUserMenu(false);
    logout();
    navigate("/login");
  };

  const handleAccountClick = () => {
    if (isAdmin) {
      navigate("/admin/dashboard");
    } else {
      navigate("/user-dashboard");
    }
    setShowUserMenu(false);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (search.trim()) {
      navigate(`/books?search=${encodeURIComponent(search)}`);
    }
  };

  const categories = [
    { name: language === "en" ? "Novel" : "நாவல்", path: "/books?category=நாவல்" },
    { name: language === "en" ? "Literature" : "இலக்கியம்", path: "/books?category=இலக்கியம்" },
    { name: language === "en" ? "Historical Novel" : "வரலாற்று நாவல்", path: "/books?category=வரலாற்று நாவல்" },
    { name: language === "en" ? "Self Help" : "சுய முன்னேற்றம்", path: "/books?category=சுய முன்னேற்றம்" },
    { name: language === "en" ? "Finance" : "நிதி", path: "/books?category=நிதி" },
    { name: language === "en" ? "Translation" : "மொழிபெயர்ப்பு", path: "/books?category=மொழிபெயர்ப்பு" },
  ];

  return (
    <nav className="navbar-container">

      {/* ================= MOBILE NAVBAR ================= */}
      <div className="mobile-navbar">
        <div className="mobile-nav-left">
          <div className="hamburger-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? '✕' : '☰'}
          </div>
          <div className="mobile-logo">
            <img src={logo} alt="Logo" className="logo-img-small" />
          </div>
        </div>
        <div className="mobile-nav-right">
          <div className="icon-item" onClick={() => navigate("/wishlist")}>
            🤍 <span className="badge">{wishlistCount}</span>
          </div>
          <div className="icon-item" onClick={() => navigate("/cart")}>
            🛒 <span className="badge">{cartCount}</span>
          </div>
        </div>
      </div>

      {/* Mobile Search Bar */}
      <div className="mobile-search-bar">
        <form onSubmit={handleSearch}>
          <input
            type="text"
            placeholder={language === "en" ? "Search books..." : "நூல்களைத் தேடுங்கள்"}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit">🔍</button>
        </form>
      </div>

      {/* Mobile Slide Menu */}
      {mobileMenuOpen && (
        <div className="mobile-slide-menu">
          <div className="mobile-menu-header">
            <button
              className="mobile-menu-close"
              onClick={() => setMobileMenuOpen(false)}
              aria-label="Close menu"
            >
              ✕
            </button>
            <button className="lang-btn" onClick={toggleLanguage}>
              {language === "en" ? "தமிழ்" : "EN"}
            </button>
            {user && (
              <div className="mobile-user-info">
                <span className="nav-user-avatar">
                  {user.first_name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || "U"}
                </span>
                <span>{user.first_name || user.username || user.email.split("@")[0]}</span>
              </div>
            )}
          </div>
          <div className="mobile-menu-links">
            <Link to="/" onClick={() => setMobileMenuOpen(false)}>{language === "en" ? "Home" : "முகப்பு"}</Link>
            <Link to="/books" onClick={() => setMobileMenuOpen(false)}>{language === "en" ? "All Books" : "அனைத்து நூல்கள்"}</Link>
            <Link to="/authors" onClick={() => setMobileMenuOpen(false)}>{language === "en" ? "Authors" : "எழுத்தாளர்கள்"}</Link>
            <Link to="/blog" onClick={() => setMobileMenuOpen(false)}>{language === "en" ? "Blog" : "வலைப்பதிவு"}</Link>
            <Link to="/testimonials" onClick={() => setMobileMenuOpen(false)}>{language === "en" ? "Testimonials" : "சான்றுகள்"}</Link>
            <Link to="/contests" onClick={() => setMobileMenuOpen(false)}>{language === "en" ? "Contests" : "போட்டிகள்"}</Link>
            <Link to="/about" onClick={() => setMobileMenuOpen(false)}>{language === "en" ? "About Us" : "எங்களை பற்றி"}</Link>
            <Link to="/contact" onClick={() => setMobileMenuOpen(false)}>{language === "en" ? "Contact" : "தொடர்பு"}</Link>
          </div>
          <div className="mobile-menu-actions">
            {user ? (
              <>
                <button onClick={() => { handleAccountClick(); setMobileMenuOpen(false); }}>
                  {isAdmin ? (language === "en" ? "Admin Panel" : "நிர்வாக பலகம்") : (language === "en" ? "My Account" : "என் கணக்கு")}
                </button>
                <button onClick={() => { navigate("/library"); setMobileMenuOpen(false); }}>
                  {language === "en" ? "My Library" : "என் நூலகம்"}
                </button>
                <button onClick={() => { handleLogout(); setMobileMenuOpen(false); }} className="logout-btn">
                  {language === "en" ? "Logout" : "வெளியேறு"}
                </button>
              </>
            ) : (
              <button onClick={() => { handleLoginClick(); setMobileMenuOpen(false); }}>
                {language === "en" ? "Login / Register" : "உள்நுழை"}
              </button>
            )}
          </div>
        </div>
      )}

      {/* ================= DESKTOP NAVBAR ================= */}
      <div className="desktop-navbar">
        {/* FIRST ROW */}
        <div className="navbar-top">
          <div className="nav-logo">
            <img src={logo} alt="Kavithedal Logo" className="logo-img" />
          </div>

          <form className="nav-search" onSubmit={handleSearch}>
            <input
              type="text"
              placeholder={
                language === "en"
                  ? "Search Tamil Books..."
                  : "தமிழ் நூல்களைத் தேடுங்கள்..."
              }
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button type="submit">📘</button>
          </form>

          <div className="nav-actions desktop-actions">
            <button className="lang-btn" onClick={toggleLanguage}>
              {language === "en" ? "தமிழ்" : "EN"}
            </button>

            <div className="icon-item" onClick={() => navigate("/wishlist")} title="Wishlist">
              🤍 <span className="badge">{wishlistCount}</span>
            </div>

            <div className="icon-item" onClick={() => navigate("/cart")} title="Cart">
              🛒 <span className="badge">{cartCount}</span>
            </div>

            {user ? (
              <div className="nav-user-menu">
                <button
                  className="nav-user-btn"
                  onClick={() => setShowUserMenu(!showUserMenu)}
                >
                  <span className="nav-user-avatar">
                    {user.first_name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || "U"}
                  </span>
                  <span className="nav-user-name">
                    {user.first_name || user.username || user.email.split("@")[0]}
                  </span>
                  <span className="nav-role-badge" data-role={user.role}>
                    {user.role === "superadmin"
                      ? (language === "en" ? "Super Admin" : "மேல் நிர்வாகி")
                      : user.role === "admin"
                        ? (language === "en" ? "Admin" : "நிர்வாகி")
                        : (language === "en" ? "User" : "பயனர்")}
                  </span>
                </button>

                {showUserMenu && (
                  <div className="nav-user-dropdown">
                    <button onClick={handleAccountClick}>
                      {isAdmin
                        ? (language === "en" ? "Admin Panel" : "நிர்வாக பலகம்")
                        : (language === "en" ? "My Account" : "என் கணக்கு")}
                    </button>
                    {!isAdmin && (
                      <button onClick={() => { navigate("/library"); setShowUserMenu(false); }}>
                        {language === "en" ? "My Library" : "என் நூலகம்"}
                      </button>
                    )}
                    <button onClick={handleLogout} className="nav-logout-btn">
                      {language === "en" ? "Logout" : "வெளியேறு"}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button className="login-btn" onClick={handleLoginClick}>
                {language === "en" ? "Login / Register" : "உள்நுழை"}
              </button>
            )}
          </div>
        </div>

        {/* SECOND ROW */}
        <div className="navbar-bottom">
          <div className="nav-links">
            <Link to="/">{language === "en" ? "Home" : "முகப்பு"}</Link>
            <Link to="/books">{language === "en" ? "Books" : "நூல்கள்"}</Link>
            <Link to="/authors">{language === "en" ? "Authors" : "எழுத்தாளர்கள்"}</Link>
            <Link to="/blog">{language === "en" ? "Blog" : "வலைப்பதிவு"}</Link>
            <Link to="/testimonials">{language === "en" ? "Testimonials" : "சான்றுகள்"}</Link>
            <Link to="/contests">{language === "en" ? "Contests" : "போட்டிகள்"}</Link>
            <Link to="/about">{language === "en" ? "About Us" : "எங்களை பற்றி"}</Link>
            <Link to="/contact">{language === "en" ? "Contact" : "தொடர்பு"}</Link>
          </div>

          {/* CATEGORIES DROPDOWN */}
          <div className="categories-wrapper">
            <button
              className="categories-btn"
              onClick={() => setShowCategories(!showCategories)}
            >
              ☰ {language === "en" ? "Categories" : "வகைகள்"}
            </button>

            {showCategories && (
              <div className="categories-dropdown">
                {categories.map((cat, index) => (
                  <Link
                    key={index}
                    to={cat.path}
                    onClick={() => setShowCategories(false)}
                  >
                    {cat.name}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
