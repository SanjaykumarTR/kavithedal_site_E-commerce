import { useState, useEffect, useContext } from "react";
import { Link } from "react-router-dom";
import api from "../api/axios";
import { LanguageContext } from "../context/LanguageContext";
import "../styles/contests.css";

export default function Contests() {
  const { language } = useContext(LanguageContext);
  const [contests, setContests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("active");

  const t = {
    en: {
      heroTitle: "Writing Contests",
      heroSubtitle: "Participate in our writing competitions and showcase your talent",
      activeContests: "Active Contests",
      allContests: "All Contests",
      loading: "Loading contests...",
      noContests: "No contests available at the moment. Check back soon!",
      prizes: "Prizes",
      rules: "Rules",
      registerNow: "Participate Now →",
      deadline: "Deadline",
      startDate: "Starts",
      expired: "Expired",
      active: "Active",
      inactive: "Inactive",
    },
    ta: {
      heroTitle: "எழுத்துப் போட்டிகள்",
      heroSubtitle: "எங்கள் எழுத்துப் போட்டிகளில் பங்கேற்று உங்கள் திறமையைக் காட்டுங்கள்",
      activeContests: "சுறுசுறுப்பான போட்டிகள்",
      allContests: "அனைத்து போட்டிகள்",
      loading: "போட்டிகள் ஏற்றுகிறது...",
      noContests: "தற்போது போட்டிகள் இல்லை. விரைவில் மீண்டும் வருக!",
      prizes: "பரிசுகள்",
      rules: "விதிகள்",
      registerNow: "பங்கேற்க →",
      deadline: "கடைசி தேதி",
      startDate: "தொடங்கும் தேதி",
      expired: "காலாவதியான",
      active: "சுறுசுறுப்பான",
      inactive: "செயலற்றது",
    },
  }[language];

  useEffect(() => {
    setLoading(true);
    const endpoint = activeTab === "active" ? "/api/contests/active/" : "/api/contests/";
    api.get(endpoint)
      .then((res) => setContests(res.data.results || res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [activeTab]);

  const formatDate = (dateString) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleDateString(
      language === "ta" ? "ta-IN" : "en-US",
      { year: "numeric", month: "short", day: "numeric" }
    );
  };

  const isExpired = (deadline) => new Date(deadline) < new Date();

  const statusBadge = (contest) => {
    if (isExpired(contest.deadline)) return <span className="status-badge expired">{t.expired}</span>;
    if (contest.is_active) return <span className="status-badge active">{t.active}</span>;
    return <span className="status-badge inactive">{t.inactive}</span>;
  };

  const parseRules = (rules) => {
    if (!rules) return [];
    return rules.split("\n").filter((r) => r.trim());
  };

  return (
    <div className="contests-page">

      {/* Hero */}
      <div className="contests-hero">
        <h1>{t.heroTitle}</h1>
        <p>{t.heroSubtitle}</p>
      </div>

      {/* Tabs */}
      <div className="contests-tabs">
        <button
          className={`tab-btn ${activeTab === "active" ? "active" : ""}`}
          onClick={() => setActiveTab("active")}
        >
          {t.activeContests}
        </button>
        <button
          className={`tab-btn ${activeTab === "all" ? "active" : ""}`}
          onClick={() => setActiveTab("all")}
        >
          {t.allContests}
        </button>
      </div>

      {/* Content */}
      <div className="contests-section">
        {loading ? (
          <div className="contests-loading">{t.loading}</div>
        ) : contests.length === 0 ? (
          <div className="contests-empty">{t.noContests}</div>
        ) : (
          <div className="contests-grid">
            {contests.map((contest) => (
              <div key={contest.id} className="contest-card">

                {/* Banner */}
                {contest.banner_url ? (
                  <div className="contest-banner">
                    <img
                      src={contest.banner_url}
                      alt={contest.title}
                      onError={(e) => { e.target.parentElement.innerHTML = '<div class="contest-banner-placeholder">🏆</div>'; }}
                    />
                  </div>
                ) : (
                  <div className="contest-banner-placeholder">🏆</div>
                )}

                {/* Body */}
                <div className="contest-content">
                  <div className="contest-status-row">
                    {statusBadge(contest)}
                    <span className={`contest-deadline-chip ${isExpired(contest.deadline) ? "expired" : ""}`}>
                      📅 {formatDate(contest.deadline)}
                    </span>
                  </div>

                  <h3 className="contest-title">{contest.title}</h3>
                  <p className="contest-description">{contest.description}</p>

                  {contest.prize_details && (
                    <div className="contest-info-block">
                      <h4>🏅 {t.prizes}</h4>
                      <p>{contest.prize_details}</p>
                    </div>
                  )}

                  {contest.rules && (
                    <div className="contest-info-block">
                      <h4>📋 {t.rules}</h4>
                      <ul className="rules-list">
                        {parseRules(contest.rules).slice(0, 4).map((rule, i) => (
                          <li key={i}>{rule}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {!isExpired(contest.deadline) && contest.is_active && (
                    <div className="contest-cta">
                      <Link to={`/contest/${contest.id}/submit`} className="participate-btn">
                        {t.registerNow}
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
