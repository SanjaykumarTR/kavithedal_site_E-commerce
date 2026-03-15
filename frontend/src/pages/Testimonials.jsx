import { useState, useEffect, useRef, useContext } from "react";
import api from "../api/axios";
import { LanguageContext } from "../context/LanguageContext";
import "../styles/testimonials.css";

export default function Testimonials() {
  const { language } = useContext(LanguageContext);
  const [testimonials, setTestimonials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "", email: "", role: "reader", message: "", rating: 5,
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const trackRef = useRef(null);
  const autoRef = useRef(null);

  const t = {
    en: {
      heroTitle: "What Our Readers Say",
      heroSubtitle: "Discover what book lovers and authors say about Kavithedal Publications",
      shareExperience: "Share Your Experience",
      cancel: "✕ Cancel",
      yourName: "Your Name", enterName: "Enter your name",
      iAmA: "I am a", reader: "Reader", author: "Author",
      yourMessage: "Your Message",
      placeholder: "Share your experience with us...",
      rating: "Rating", submit: "Submit Testimonial",
      submitting: "Submitting...",
      thankYou: "Thank you! Your testimonial has been submitted for review.",
      loading: "Loading testimonials...",
      noTestimonials: "No testimonials yet. Be the first to share your experience!",
      allReviews: "All Reviews",
      stats: { total: "Happy Readers", avgRating: "Avg Rating", authors: "Authors", reviews: "Reviews" },
    },
    ta: {
      heroTitle: "எங்கள் வாசகர்கள் என்ன சொல்கிறார்கள்",
      heroSubtitle: "கவித்திடல் பதிப்பகத்தைப் பற்றி புத்தகக் காதலர்கள் மற்றும் எழுத்தாளர்கள் சொல்வதை அறியுங்கள்",
      shareExperience: "உங்கள் அனுபவத்தைப் பகிருங்கள்",
      cancel: "✕ ரத்து",
      yourName: "உங்கள் பெயர்", enterName: "உங்கள் பெயரை உள்ளிடுக",
      iAmA: "நான் ஒரு", reader: "வாசகர்", author: "எழுத்தாளர்",
      yourMessage: "உங்கள் செய்தி",
      placeholder: "உங்கள் அனுபவத்தை எங்களுடன் பகிருங்கள்...",
      rating: "மதிப்பீடு", submit: "சான்றைச் சமர்ப்பிக்க",
      submitting: "சமர்ப்பித்து...",
      thankYou: "நன்றி! உங்கள் சான்று மதிப்பாய்வுக்காகச் சமர்ப்பிக்கப்பட்டது.",
      loading: "சான்றுகள் ஏற்றுகிறது...",
      noTestimonials: "இன்னும் சான்றுகள் இல்லை. உங்கள் அனுபவத்தை முதலில் பகிருங்கள்!",
      allReviews: "அனைத்து மதிப்புரைகள்",
      stats: { total: "மகிழ்ச்சியான வாசகர்கள்", avgRating: "சராசரி மதிப்பீடு", authors: "எழுத்தாளர்கள்", reviews: "மதிப்புரைகள்" },
    },
  }[language];

  /* -------- video embed helper -------- */
  const getVideoEmbedUrl = (url, videoType) => {
    if (!url) return null;
    if (videoType === "youtube") {
      const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
      if (match) return `https://www.youtube.com/embed/${match[1]}`;
    } else if (videoType === "vimeo") {
      const match = url.match(/vimeo\.com\/(\d+)/);
      if (match) return `https://player.vimeo.com/video/${match[1]}`;
    }
    return url;
  };

  /* -------- fetch -------- */
  useEffect(() => {
    api.get("/api/testimonials/")
      .then((res) => setTestimonials(res.data.results || res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  /* -------- carousel auto-play -------- */
  const VISIBLE = 3;
  const total = testimonials.length;
  const maxIndex = Math.max(0, total - VISIBLE);

  const startAuto = () => {
    clearInterval(autoRef.current);
    autoRef.current = setInterval(() => {
      setCurrentIndex((p) => (p >= maxIndex ? 0 : p + 1));
    }, 4000);
  };

  useEffect(() => {
    if (total > VISIBLE) startAuto();
    return () => clearInterval(autoRef.current);
  }, [total, maxIndex]);

  useEffect(() => {
    if (trackRef.current) {
      const cardWidth = 324; // 300px + 24px gap
      trackRef.current.style.transform = `translateX(-${currentIndex * cardWidth}px)`;
    }
  }, [currentIndex]);

  const prev = () => {
    setCurrentIndex((p) => (p <= 0 ? maxIndex : p - 1));
    startAuto();
  };
  const next = () => {
    setCurrentIndex((p) => (p >= maxIndex ? 0 : p + 1));
    startAuto();
  };

  /* -------- form submit -------- */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/api/testimonials/", formData);
      setSuccess(true);
      setFormData({ name: "", email: "", role: "reader", message: "", rating: 5 });
      setTimeout(() => { setShowForm(false); setSuccess(false); }, 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  /* -------- computed stats -------- */
  const avgRating = total
    ? (testimonials.reduce((s, t) => s + (t.rating || 0), 0) / total).toFixed(1)
    : "—";
  const authorCount = testimonials.filter((t) => t.role === "author").length;

  /* -------- helpers -------- */
  const stars = (n) => "⭐".repeat(n);
  const roleLabel = (role) =>
    role === "author"
      ? language === "ta" ? "எழுத்தாளர்" : "Author"
      : language === "ta" ? "வாசகர்" : "Reader";

  return (
    <div className="testimonials-page">

      {/* Hero */}
      <div className="testimonials-hero">
        <h1>{t.heroTitle}</h1>
        <p>{t.heroSubtitle}</p>
      </div>

      {/* Stats bar */}
      <div className="testimonials-stats">
        <div className="stat-item">
          <div className="stat-number">{total}+</div>
          <div className="stat-label">{t.stats.total}</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">{avgRating}</div>
          <div className="stat-label">{t.stats.avgRating}</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">{authorCount}</div>
          <div className="stat-label">{t.stats.authors}</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">{total}</div>
          <div className="stat-label">{t.stats.reviews}</div>
        </div>
      </div>

      {/* Submit button */}
      <div className="testimonials-action">
        <button
          className="submit-testimonial-btn"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? t.cancel : "📝 " + t.shareExperience}
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="testimonial-form-container">
          <form onSubmit={handleSubmit} className="testimonial-form">
            <h3>{t.shareExperience}</h3>
            {success && <div className="success-message">{t.thankYou}</div>}
            <div className="form-group">
              <label>{t.yourName}</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                placeholder={t.enterName}
              />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="Enter your email"
              />
            </div>
            <div className="form-group">
              <label>{t.iAmA}</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              >
                <option value="reader">{t.reader}</option>
                <option value="author">{t.author}</option>
              </select>
            </div>
            <div className="form-group">
              <label>{t.yourMessage}</label>
              <textarea
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                required
                placeholder={t.placeholder}
                rows={4}
              />
            </div>
            <div className="form-group">
              <label>{t.rating}</label>
              <div className="rating-select">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    className={`star-btn ${formData.rating >= star ? "active" : ""}`}
                    onClick={() => setFormData({ ...formData, rating: star })}
                  >
                    ⭐
                  </button>
                ))}
              </div>
            </div>
            <button type="submit" className="submit-btn" disabled={submitting}>
              {submitting ? t.submitting : t.submit}
            </button>
          </form>
        </div>
      )}

      {/* Carousel */}
      <div className="testimonials-carousel-section">
        <h2>{t.allReviews}</h2>

        {loading ? (
          <p style={{ textAlign: "center", color: "#888" }}>{t.loading}</p>
        ) : total === 0 ? (
          <p style={{ textAlign: "center", color: "#888" }}>{t.noTestimonials}</p>
        ) : (
          <>
            <div className="carousel-wrapper">
              <div className="carousel-track" ref={trackRef}>
                {testimonials.map((item) => (
                  <div key={item.id} className="testimonial-card">
                    <div className="testimonial-header">
                      {item.photo_url ? (
                        <img
                          src={item.photo_url}
                          alt={item.name}
                          className="testimonial-avatar"
                          onError={(e) => {
                            e.target.style.display = "none";
                            e.target.nextSibling && (e.target.nextSibling.style.display = "flex");
                          }}
                        />
                      ) : null}
                      <div
                        className="testimonial-avatar-initial"
                        style={{ display: item.photo_url ? "none" : "flex" }}
                      >
                        {item.name.charAt(0).toUpperCase()}
                      </div>
                      <div className="testimonial-info">
                        <h4>{item.name}</h4>
                        <span className="testimonial-role">{roleLabel(item.role)}</span>
                      </div>
                      <div className="testimonial-rating">{stars(item.rating)}</div>
                    </div>
                    <p className="testimonial-message">{item.message}</p>
                    {item.has_video && (item.video_url || item.video_file_url) && (
                      <div className="testimonial-video">
                        {(item.video_type === "youtube" || item.video_type === "vimeo") ? (
                          <iframe
                            src={getVideoEmbedUrl(item.video_url, item.video_type)}
                            title="Testimonial Video"
                            style={{ border: 0 }}
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                          />
                        ) : (
                          <video controls src={item.video_file_url || item.video_url} style={{ width: '100%', borderRadius: '8px' }}>
                            Your browser does not support the video tag.
                          </video>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {total > VISIBLE && (
              <div className="carousel-controls">
                <button className="carousel-btn" onClick={prev} aria-label="Previous">‹</button>
                <div className="carousel-dots">
                  {Array.from({ length: maxIndex + 1 }).map((_, i) => (
                    <span
                      key={i}
                      className={`carousel-dot ${i === currentIndex ? "active" : ""}`}
                      onClick={() => { setCurrentIndex(i); startAuto(); }}
                    />
                  ))}
                </div>
                <button className="carousel-btn" onClick={next} aria-label="Next">›</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
