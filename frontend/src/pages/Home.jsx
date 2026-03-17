import { useContext, useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import PromoSection from "../components/PromoSection";
import ImageSlider from "../components/ImageSlider";
import ProductCard from "../components/ProductCard";
import api from "../api/axios";
import { mediaUrl } from "../utils/mediaUrl";
import "../styles/home.css";
import "../styles/testimonials.css";
import "../styles/contests.css";


export default function Home() {
  const { language } = useContext(LanguageContext);
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        const response = await api.get("/api/books/");
        const booksData = response.data.results || response.data;
        setBooks(booksData);
      } catch (err) {
        console.error("Error fetching books:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchBooks();
  }, []);

  // Map backend data to frontend format
  const mappedBooks = Array.isArray(books) ? books.map((book) => {
    const originalPrice = Number(book.price) || 0;
    const discountPercent = Number(book.discount_percentage) || 0;
    const discountedPrice = discountPercent > 0 
      ? originalPrice - (originalPrice * discountPercent / 100) 
      : originalPrice;
    
    // Get ebook and physical prices from API
    const ebookPrice = book.ebook_price ? Number(book.ebook_price) : null;
    const physicalPrice = book.physical_price ? Number(book.physical_price) : null;
    
    return {
      id: book.id,
      title: book.title,
      author: book.author_name || book.author?.name || "Unknown Author",
      price: discountPercent > 0 ? discountedPrice : originalPrice,
      oldPrice: originalPrice,
      discount: discountPercent,
      rating: 4.5,
      image: mediaUrl(book.cover_image),
      category: book.category_name || "Uncategorized",
      ebook_price: ebookPrice,
      physical_price: physicalPrice,
      discount_percentage: discountPercent
    };
  }) : [];

  const featuredBooks = mappedBooks.filter((b) => b.rating >= 4.5).slice(0, 4);
  const newArrivals = mappedBooks.slice(4, 8);

  /* ===============================
     PREMIUM FEATURED ADS
  ================================ */
  const premiumAds = [
    {
      image: "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=600",
      titleEn: "Mega Book Sale",
      titleTa: "மாபெரும் புத்தக விற்பனை",
      discount: "50%",
    },
    {
      image: "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=600",
      titleEn: "Weekend Special",
      titleTa: "வார இறுதி சலுகை",
      discount: "30%",
    },
    {
      image: "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=600",
      titleEn: "New Arrivals Offer",
      titleTa: "புதிய வரவுகள் சலுகை",
      discount: "20%",
    }
  ];

  const [currentPremiumAd, setCurrentPremiumAd] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentPremiumAd(
        (prev) => (prev + 1) % premiumAds.length
      );
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  /* ===============================
     SIMPLE NEW ARRIVAL ADS
  ================================ */
  
    
  const sideAds = [
  {
    image: "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=600&q=80",
    titleEn: "Free Bookmark",
    titleTa: "இலவச புத்தக குறியீடு",
    descEn: "Get free bookmark with every order.",
    descTa: "ஒவ்வொரு ஆர்டருக்கும் இலவச புத்தக குறியீடு."
  },
  {
    image: "https://images.unsplash.com/photo-1496104679561-38b3b4a9b4a1?auto=format&fit=crop&w=600&q=80",
    titleEn: "Student Discount",
    titleTa: "மாணவர் தள்ளுபடி",
    descEn: "Flat 25% off for students.",
    descTa: "மாணவர்களுக்கு 25% தள்ளுபடி."
  },
  {
    image: "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=600&q=80",
    titleEn: "Combo Offer",
    titleTa: "காம்போ சலுகை",
    descEn: "Buy 3 books & save more.",
    descTa: "3 புத்தகங்கள் வாங்கி சேமிக்கவும்."
  },
  {
    image: "https://images.unsplash.com/photo-1455885666463-6e4f7d3d0e4f?auto=format&fit=crop&w=600&q=80",
    titleEn: "Festive Sale",
    titleTa: "விழா சலுகை",
    descEn: "Special festive discounts.",
    descTa: "விழா சிறப்பு தள்ளுபடி."
  },
  {
    image: "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&w=600&q=80",
    titleEn: "Author Meet",
    titleTa: "எழுத்தாளர் சந்திப்பு",
    descEn: "Meet your favorite authors.",
    descTa: "உங்கள் விருப்ப எழுத்தாளர்களை சந்திக்கவும்."
  }
];


  const [currentSideAd, setCurrentSideAd] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentSideAd((prev) => (prev + 1) % sideAds.length);
    }, 3500);

    return () => clearInterval(interval);
  }, []);

  /* ===============================
     TESTIMONIALS
  ================================ */
  const [testimonials, setTestimonials] = useState([]);
  const [testiIndex, setTestiIndex] = useState(0);
  const testiTrackRef = useRef(null);
  const testiAutoRef = useRef(null);

  useEffect(() => {
    api.get("/api/testimonials/")
      .then((res) => setTestimonials((res.data.results || res.data).slice(0, 9)))
      .catch(() => {});
  }, []);

  const TESTI_VISIBLE = 3;
  const testiMax = Math.max(0, testimonials.length - TESTI_VISIBLE);

  useEffect(() => {
    if (testimonials.length > TESTI_VISIBLE) {
      testiAutoRef.current = setInterval(() => {
        setTestiIndex((p) => (p >= testiMax ? 0 : p + 1));
      }, 4000);
    }
    return () => clearInterval(testiAutoRef.current);
  }, [testimonials.length, testiMax]);

  useEffect(() => {
    if (testiTrackRef.current) {
      testiTrackRef.current.style.transform = `translateX(-${testiIndex * 324}px)`;
    }
  }, [testiIndex]);

  const testiPrev = () => {
    setTestiIndex((p) => (p <= 0 ? testiMax : p - 1));
  };
  const testiNext = () => {
    setTestiIndex((p) => (p >= testiMax ? 0 : p + 1));
  };

  /* ===============================
     CONTESTS PREVIEW
  ================================ */
  const [homeContests, setHomeContests] = useState([]);

  useEffect(() => {
    api.get("/api/contests/active/")
      .then((res) => setHomeContests((res.data.results || res.data).slice(0, 3)))
      .catch(() => {});
  }, []);

  return (
    <>
      {/* Parallax Background Shapes */}
      <div className="parallax-bg">
        <div className="parallax-shape parallax-shape-1"></div>
        <div className="parallax-shape parallax-shape-2"></div>
      </div>

      {/* ImageSlider and PromoSection render immediately — never block on books API */}
      <ImageSlider />
      <PromoSection />

      {/* ================= BOOKS SECTIONS ================= */}
      {loading ? (
        <div className="books-loading-row">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="book-card-skeleton" />
          ))}
        </div>
      ) : books.length === 0 ? (
        <div className="no-books">
          {language === "en"
            ? "No books available. Please add books in the admin panel."
            : "புத்தகங்கள் இல்லை. நிர்வாக பகுதியில் புத்தகங்கள் சேர்க்கவும்."}
        </div>
      ) : (
        <>

      {/* ================= FEATURED SECTION ================= */}
      <section className="home-section home-featured-layout">
        {/* Floating Decorations */}
        <div className="floating-decoration" style={{ top: '10%', left: '2%' }}>
          <div className="floating-book"></div>
        </div>
        <div className="floating-decoration" style={{ top: '60%', right: '2%' }}>
          <div className="floating-circle" style={{ width: '80px', height: '80px' }}></div>
        </div>
        <div className="floating-decoration" style={{ top: '30%', right: '5%' }}>
          <span className="floating-star">✦</span>
        </div>

        <div className="featured-left">
          <h2 className="section-title">
            {language === "en" ? "Featured Books" : "சிறப்பு நூல்கள்"}
          </h2>

          <div className="product-row">
            {featuredBooks.map((book) => (
              <ProductCard key={book.id} book={book} />
            ))}
          </div>

          <div className="section-action">
            <Link to="/books" className="view-all-btn">
              {language === "en"
                ? "View All Books"
                : "அனைத்து நூல்களையும் காண"}
            </Link>
          </div>
        </div>

        {/* Premium Image Ad */}
        <div className="featured-right">
          <div className="premium-ad-card">
            <img
              src={premiumAds[currentPremiumAd].image}
              alt="Offer"
              width="600"
              height="380"
              loading="lazy"
              decoding="async"
            />
            <div className="ad-overlay">
              <h3>
                {language === "en"
                  ? premiumAds[currentPremiumAd].titleEn
                  : premiumAds[currentPremiumAd].titleTa}
              </h3>
              <span className="ad-discount-badge">
                {premiumAds[currentPremiumAd].discount} OFF
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ================= NEW ARRIVALS SECTION ================= */}
      <section className="home-section home-new-layout">
        {/* Floating Decorations */}
        <div className="floating-decoration" style={{ top: '15%', left: '3%' }}>
          <div className="floating-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
        <div className="floating-decoration" style={{ bottom: '20%', right: '3%' }}>
          <div className="floating-book" style={{ 
            background: 'linear-gradient(135deg, #FFD54F 0%, #FFB300 100%)',
            animationDelay: '1s'
          }}></div>
        </div>
        <div className="floating-decoration" style={{ top: '40%', left: '1%' }}>
          <span className="floating-star" style={{ 
            color: '#B71C1C',
            animationDelay: '0.5s'
          }}>✦</span>
        </div>

        <div className="new-left">
          <h2 className="section-title">
            {language === "en" ? "New Arrivals" : "புதிய வரவுகள்"}
          </h2>

          <div className="product-row">
            {newArrivals.map((book) => (
              <ProductCard key={book.id} book={book} />
            ))}
          </div>
        </div>

        {/* Simple Text Ad */}
        <div className="new-right">
          <div className="premium-ad-card">
            <img
              src={sideAds[currentSideAd].image}
              alt="Offer"
              width="600"
              height="380"
              loading="lazy"
              decoding="async"
              onError={(e) => {
                e.target.src =
                  "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80";
              }}
            />

            <div className="ad-overlay">
              <h3>
                {language === "en"
                  ? sideAds[currentSideAd].titleEn
                  : sideAds[currentSideAd].titleTa}
              </h3>

              <span className="ad-discount-badge">
                {language === "en" ? "Special Offer" : "சிறப்பு சலுகை"}
              </span>

              <p className="countdown">
                {language === "en"
                  ? sideAds[currentSideAd].descEn
                  : sideAds[currentSideAd].descTa}
              </p>
            </div>

            {/* Optional Dots */}
            <div className="ad-dots">
              {sideAds.map((_, index) => (
                <span
                  key={index}
                  className={`dot ${
                    index === currentSideAd ? "active" : ""
                  }`}
                  onClick={() => setCurrentSideAd(index)}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

        </>
      )} {/* end books loading/empty/content block */}

      {/* ================= TESTIMONIALS SECTION ================= */}
      {testimonials.length > 0 && (
        <section className="home-testimonials-section">
          <div className="home-testimonials-inner">
            <div className="section-heading">
              <h2>{language === "en" ? "What Readers Say" : "வாசகர்கள் சொல்வது"}</h2>
              <p>{language === "en" ? "Trusted by book lovers across Tamil Nadu" : "தமிழ்நாடு முழுவதும் புத்தகக் காதலர்கள் நம்புகிறார்கள்"}</p>
              <div className="underline" />
            </div>

            <div className="carousel-wrapper">
              <div className="home-testimonials-track carousel-track" ref={testiTrackRef}>
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
                            const sib = e.target.nextElementSibling;
                            if (sib) sib.style.display = "flex";
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
                        <span className="testimonial-role">
                          {item.role === "author"
                            ? (language === "ta" ? "எழுத்தாளர்" : "Author")
                            : (language === "ta" ? "வாசகர்" : "Reader")}
                        </span>
                      </div>
                      <div className="testimonial-rating">{"⭐".repeat(item.rating)}</div>
                    </div>
                    <p className="testimonial-message">{item.message}</p>
                  </div>
                ))}
              </div>
            </div>

            {testimonials.length > TESTI_VISIBLE && (
              <div className="carousel-controls">
                <button className="carousel-btn" onClick={testiPrev}>‹</button>
                <div className="carousel-dots">
                  {Array.from({ length: testiMax + 1 }).map((_, i) => (
                    <span
                      key={i}
                      className={`carousel-dot ${i === testiIndex ? "active" : ""}`}
                      onClick={() => setTestiIndex(i)}
                    />
                  ))}
                </div>
                <button className="carousel-btn" onClick={testiNext}>›</button>
              </div>
            )}

            <div className="view-all-testimonials">
              <Link to="/testimonials">
                {language === "en" ? "View All Reviews" : "அனைத்து மதிப்புரைகளையும் காண"}
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ================= CONTESTS PREVIEW SECTION ================= */}
      {homeContests.length > 0 && (
        <section className="home-contests-section">
          <div className="home-contests-inner">
            <div className="section-heading">
              <h2>{language === "en" ? "Active Contests" : "சுறுசுறுப்பான போட்டிகள்"}</h2>
              <p>{language === "en" ? "Showcase your writing talent and win prizes" : "உங்கள் எழுத்துத் திறமையை வெளிப்படுத்தி பரிசு வெல்லுங்கள்"}</p>
              <div className="underline" />
            </div>

            <div className="home-contests-grid">
              {homeContests.map((contest) => (
                <div key={contest.id} className="contest-card">
                  {contest.banner_url ? (
                    <div className="contest-banner">
                      <img
                        src={contest.banner_url}
                        alt={contest.title}
                        width="600"
                        height="300"
                        loading="lazy"
                        decoding="async"
                        onError={(e) => { e.target.parentElement.innerHTML = '<div class="contest-banner-placeholder">🏆</div>'; }}
                      />
                    </div>
                  ) : (
                    <div className="contest-banner-placeholder">🏆</div>
                  )}
                  <div className="contest-content">
                    <div className="contest-status-row">
                      <span className="status-badge active">
                        {language === "en" ? "Active" : "சுறுசுறுப்பான"}
                      </span>
                      <span className="contest-deadline-chip">
                        📅 {new Date(contest.deadline).toLocaleDateString(
                          language === "ta" ? "ta-IN" : "en-US",
                          { month: "short", day: "numeric", year: "numeric" }
                        )}
                      </span>
                    </div>
                    <h3 className="contest-title">{contest.title}</h3>
                    <p className="contest-description">{contest.description}</p>
                    <div className="contest-cta">
                      <Link to={`/contest/${contest.id}/submit`} className="participate-btn">
                        {language === "en" ? "Participate Now →" : "பங்கேற்க →"}
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="view-all-contests">
              <Link to="/contests">
                {language === "en" ? "View All Contests" : "அனைத்து போட்டிகளையும் காண"}
              </Link>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
