import { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";
import "../styles/productCard.css";

export default function PurchaseTypeSelector({ book, onClose }) {
  const { language } = useContext(LanguageContext);
  const { user } = useAuth();
  const navigate = useNavigate();

  const translations = {
    en: {
      title: "Select Purchase Type",
      ebook: "eBook",
      physical: "Physical Book",
      ebookDesc: "Instant access, read online",
      physicalDesc: "Delivered to your address",
      proceed: "Proceed",
      cancel: "Cancel",
      selectOption: "Please select an option to continue",
      loginRequired: "Please login to purchase",
      noPrices: "No purchase options available for this book.",
    },
    ta: {
      title: "வாங்கும் வகையைத் தேர்ந்தெடுக்கவும்",
      ebook: "இ-புத்தகம்",
      physical: "இயல்பான புத்தகம்",
      ebookDesc: "உடனடி அணுகல், ஆன்லைனில் படிக்கவும்",
      physicalDesc: "உங்கள் முகவரிக்கு விநியோகம்",
      proceed: "தொடர்வது",
      cancel: "ரத்து",
      selectOption: "தொடர ஒரு விருப்பத்தைத் தேர்ந்தெடுக்கவும்",
      loginRequired: "வாங்க உள்நுழையவும்",
      noPrices: "இந்த புத்தகத்திற்கு வாங்கும் விருப்பங்கள் இல்லை.",
    }
  };

  const t = translations[language];
  const [selectedType, setSelectedType] = useState(null);

  // ── Determine which options to show ──────────────────────────────────────
  // book_type ('ebook' | 'physical' | 'both') is the primary signal.
  // Prices may come as strings ("150.00") or null from the Django API.
  const bookType = book.book_type || "both";

  const rawEbookPrice  = parseFloat(book.ebook_price)   || 0;
  const rawPhysicalPrice = parseFloat(book.physical_price) || parseFloat(book.price) || 0;

  // Show eBook card if book_type includes ebook OR a positive ebook_price exists
  const showEbook    = bookType === "ebook"    || bookType === "both" || rawEbookPrice > 0;
  // Show Physical card if book_type includes physical OR a positive physical/base price exists
  const showPhysical = bookType === "physical" || bookType === "both" || rawPhysicalPrice > 0;

  // Best price to display (prefer discounted/final price when available)
  const displayEbookPrice    = parseFloat(book.ebook_final_price)    || rawEbookPrice    || rawPhysicalPrice;
  const displayPhysicalPrice = parseFloat(book.physical_final_price) || rawPhysicalPrice || rawEbookPrice;

  // ── Navigation ────────────────────────────────────────────────────────────
  const handleProceed = () => {
    if (!user) {
      navigate("/login");
      return;
    }
    if (selectedType === "ebook") {
      navigate(`/ebook-purchase/${book.id}`);
    } else if (selectedType === "physical") {
      navigate(`/physical-purchase/${book.id}`);
    }
  };

  return (
    <div className="purchase-type-overlay" onClick={onClose}>
      <div className="purchase-type-modal" onClick={(e) => e.stopPropagation()}>
        <h2>{t.title}</h2>

        <div className="purchase-type-options">
          {showEbook && (
            <div
              className={`purchase-type-card ${selectedType === "ebook" ? "selected" : ""}`}
              onClick={() => setSelectedType("ebook")}
            >
              <div className="type-icon">📱</div>
              <h3>{t.ebook}</h3>
              {displayEbookPrice > 0 && (
                <p className="type-price">₹{displayEbookPrice}</p>
              )}
              <p className="type-desc">{t.ebookDesc}</p>
            </div>
          )}

          {showPhysical && (
            <div
              className={`purchase-type-card ${selectedType === "physical" ? "selected" : ""}`}
              onClick={() => setSelectedType("physical")}
            >
              <div className="type-icon">📦</div>
              <h3>{t.physical}</h3>
              {displayPhysicalPrice > 0 && (
                <p className="type-price">₹{displayPhysicalPrice}</p>
              )}
              <p className="type-desc">{t.physicalDesc}</p>
            </div>
          )}

          {!showEbook && !showPhysical && (
            <p style={{ color: "#888", textAlign: "center", padding: "1rem" }}>
              {t.noPrices}
            </p>
          )}
        </div>

        <div className="purchase-type-actions">
          <button className="btn-cancel" onClick={onClose}>
            {t.cancel}
          </button>
          <button
            className="btn-proceed"
            onClick={handleProceed}
            disabled={!selectedType}
          >
            {t.proceed}
          </button>
        </div>
      </div>
    </div>
  );
}
