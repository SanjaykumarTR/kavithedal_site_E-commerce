import { useSearchParams, Link } from "react-router-dom";
import { useContext } from "react";
import { LanguageContext } from "../context/LanguageContext";
import "../styles/bookDetail.css";

/**
 * PaymentFailure — shown when a payment is explicitly cancelled or failed.
 * Cashfree may redirect here if the merchant sets a failure return_url,
 * or the app can redirect here after a failed verification.
 */
export default function PaymentFailure() {
  const [searchParams] = useSearchParams();
  const { language } = useContext(LanguageContext);

  const orderId = searchParams.get("order_id");
  const reason = searchParams.get("reason") || "";

  const translations = {
    en: {
      title: "Payment Failed",
      message: "Your payment could not be processed. No amount has been deducted.",
      reason: "Reason",
      orderId: "Order Reference",
      tryAgain: "Try Again",
      backToHome: "Back to Home",
      support:
        "If you believe this is an error, please contact us at kavithedalpublications@gmail.com",
      tips: [
        "Check your internet connection and try again.",
        "Ensure your card/UPI has sufficient balance.",
        "Try a different payment method.",
      ],
    },
    ta: {
      title: "கட்டணம் தோல்வியடைந்தது",
      message: "உங்கள் கட்டணம் செயல்படுத்தப்படவில்லை. எந்த தொகையும் கழிக்கப்படவில்லை.",
      reason: "காரணம்",
      orderId: "ஆணை குறிப்பு",
      tryAgain: "மீண்டும் முயற்சி",
      backToHome: "முகப்பு பக்கம்",
      support:
        "இது பிழை என்று நம்பினால், kavithedalpublications@gmail.com என்று தொடர்பு கொள்ளவும்",
      tips: [
        "இணைய இணைப்பை சரிபார்த்து மீண்டும் முயற்சி செய்யவும்.",
        "உங்கள் கார்டு/UPI இல் போதுமான இருப்பு உள்ளதா என்று சரிபார்க்கவும்.",
        "வேறு கட்டண முறையை முயற்சிக்கவும்.",
      ],
    },
  };

  const t = translations[language];

  return (
    <div className="purchase-success-page">
      <div className="success-container" style={{ borderTop: "4px solid #c0392b" }}>
        <div className="success-icon" style={{ fontSize: "3rem", color: "#c0392b" }}>
          ✗
        </div>
        <h1 style={{ color: "#c0392b" }}>{t.title}</h1>
        <p className="success-message">{t.message}</p>

        {(orderId || reason) && (
          <div className="order-details">
            {orderId && (
              <p>
                <strong>{t.orderId}:</strong> {orderId}
              </p>
            )}
            {reason && (
              <p>
                <strong>{t.reason}:</strong> {reason}
              </p>
            )}
          </div>
        )}

        <ul
          style={{
            textAlign: "left",
            marginTop: "1rem",
            marginBottom: "1.5rem",
            paddingLeft: "1.5rem",
            color: "#555",
            fontSize: "0.9rem",
          }}
        >
          {t.tips.map((tip, i) => (
            <li key={i}>{tip}</li>
          ))}
        </ul>

        <p
          style={{
            fontSize: "0.82rem",
            color: "#888",
            marginBottom: "1.5rem",
          }}
        >
          {t.support}
        </p>

        <div className="success-actions">
          <Link to="/books" className="btn-success">
            {t.tryAgain}
          </Link>
          <Link to="/" className="btn-secondary">
            {t.backToHome}
          </Link>
        </div>
      </div>
    </div>
  );
}
