import { useEffect, useState, useContext } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import { CartContext } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { verifyCashfreePayment } from "../api/orders";
import "../styles/bookDetail.css";

/**
 * PurchaseSuccess — landing page after Cashfree redirects the user back.
 *
 * URL params (set by backend return_url + Cashfree):
 *   ?order_id=kv-eb-xxx   — the Cashfree order ID
 *   &type=ebook|physical|cart
 *   &book=Book+Title       — (optional) book title for display
 */
export default function PurchaseSuccess() {
  const [searchParams] = useSearchParams();
  const { language } = useContext(LanguageContext);
  const { cart, removeFromCart } = useContext(CartContext);
  const { user } = useAuth();
  const navigate = useNavigate();

  const orderId = searchParams.get("order_id");
  const purchaseType = searchParams.get("type") || "ebook";
  const bookTitle = searchParams.get("book") || "your book";

  const [verifying, setVerifying] = useState(true);
  const [verified, setVerified] = useState(false);
  const [bookName, setBookName] = useState(decodeURIComponent(bookTitle));
  const [errorMsg, setErrorMsg] = useState("");
  const [retryCount, setRetryCount] = useState(0);

  const translations = {
    en: {
      verifying: "Verifying your payment...",
      success: "Payment Successful!",
      ebookMsg: "Your eBook has been added to your library. You can read it anytime.",
      physicalMsg: "Your order has been placed. We will ship it to your address shortly.",
      cartMsg: "Your order has been placed successfully.",
      orderId: "Order Reference",
      bookName: "Book",
      thankYou: "Thank you for shopping with Kavithedal Publications!",
      goToLibrary: "Go to Library",
      goToOrders: "View My Orders",
      backToHome: "Back to Home",
      verifyFailed: "Payment Verification Failed",
      retrying: "Checking payment status...",
      retry: "Retry Verification",
      contactSupport: "If you were charged, please contact support with your order ID.",
    },
    ta: {
      verifying: "உங்கள் கட்டணத்தை சரிபார்க்கிறது...",
      success: "கட்டணம் வெற்றியாக உள்ளது!",
      ebookMsg: "உங்கள் இ-புத்தகம் நூலகத்தில் சேர்க்கப்பட்டது.",
      physicalMsg: "உங்கள் ஆணை வெற்றியாக செய்யப்பட்டது.",
      cartMsg: "உங்கள் ஆணை வெற்றியாக செய்யப்பட்டது.",
      orderId: "ஆணை குறிப்பு",
      bookName: "புத்தகம்",
      thankYou: "கவித்தேல் பதிப்பகத்தில் வாங்கியதற்கு நன்றி!",
      goToLibrary: "நூலகத்திற்கு செல்",
      goToOrders: "என் ஆணைகளை பார்",
      backToHome: "முகப்பு பக்கம்",
      verifyFailed: "கட்டண சரிபார்ப்பு தோல்வியடைந்தது",
      retrying: "கட்டண நிலையை சரிபார்க்கிறது...",
      retry: "மீண்டும் சரிபார்",
      contactSupport: "கட்டணம் செய்யப்பட்டிருந்தால், ஆதரவை தொடர்பு கொள்ளவும்.",
    },
  };

  const t = translations[language];

  useEffect(() => {
    if (!orderId) {
      setErrorMsg("No order ID found in URL.");
      setVerifying(false);
      return;
    }
    if (!user) {
      // Wait for auth to load — redirect to login if not logged in
      navigate(`/login?next=/payment-success?order_id=${orderId}&type=${purchaseType}`);
      return;
    }
    verifyPayment();
  }, [orderId, user, retryCount]);

  const verifyPayment = async () => {
    setVerifying(true);
    setErrorMsg("");
    try {
      const data = await verifyCashfreePayment(orderId);

      if (data.paid) {
        setVerified(true);
        // Use the book title returned by backend if available
        if (data.book_title) setBookName(data.book_title);
        // Clear cart if this was a cart checkout
        if (purchaseType === "cart" || data.purchase_type === "cart") {
          cart.forEach((item) => removeFromCart(item.id));
        }
      } else {
        // Payment not yet confirmed (ACTIVE, EXPIRED, etc.)
        const statusMsg =
          data.status === "ACTIVE"
            ? "Payment is still processing. Please wait a moment and retry."
            : data.status === "EXPIRED"
            ? "Payment session expired. Please try purchasing again."
            : `Payment status: ${data.status}. Please retry or contact support.`;
        setErrorMsg(statusMsg);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setErrorMsg("Order not found. If you were charged, please contact support.");
      } else if (err.response?.status === 503) {
        setErrorMsg("Payment gateway temporarily unavailable. Please retry in a moment.");
      } else {
        setErrorMsg(err.response?.data?.error || "Failed to verify payment. Please retry.");
      }
    } finally {
      setVerifying(false);
    }
  };

  // ── Loading state ───────────────────────────────────────────────────────────
  if (verifying) {
    return (
      <div className="purchase-success-page">
        <div className="success-container">
          <div className="spinner"></div>
          <p style={{ marginTop: "1rem", color: "#666" }}>{t.verifying}</p>
        </div>
      </div>
    );
  }

  // ── Error / unverified state ────────────────────────────────────────────────
  if (!verified) {
    return (
      <div className="purchase-success-page">
        <div className="success-container" style={{ borderTop: "4px solid #c0392b" }}>
          <div className="success-icon" style={{ color: "#c0392b" }}>✗</div>
          <h1 style={{ color: "#c0392b" }}>{t.verifyFailed}</h1>
          <p className="success-message">{errorMsg}</p>

          {orderId && (
            <div className="order-details">
              <p>
                <strong>{t.orderId}:</strong> {orderId}
              </p>
            </div>
          )}

          <p style={{ fontSize: "0.85rem", color: "#888", marginTop: "0.5rem" }}>
            {t.contactSupport}
          </p>

          <div className="success-actions">
            <button
              className="btn-success"
              onClick={() => setRetryCount((c) => c + 1)}
            >
              {t.retry}
            </button>
            <Link to="/" className="btn-secondary">{t.backToHome}</Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Success state ───────────────────────────────────────────────────────────
  const isEbook = purchaseType === "ebook";
  const successMessage = isEbook
    ? t.ebookMsg
    : purchaseType === "cart"
    ? t.cartMsg
    : t.physicalMsg;

  return (
    <div className="purchase-success-page">
      <div className="success-container">
        <div className="success-icon">✓</div>
        <h1>{t.success}</h1>
        <p className="success-message">{successMessage}</p>

        <div className="order-details">
          {orderId && (
            <p>
              <strong>{t.orderId}:</strong> {orderId}
            </p>
          )}
          {purchaseType !== "cart" && (
            <p>
              <strong>{t.bookName}:</strong> {bookName}
            </p>
          )}
        </div>

        <p className="thank-you">{t.thankYou}</p>

        <div className="success-actions">
          {isEbook ? (
            <Link to="/library" className="btn-success">
              {t.goToLibrary}
            </Link>
          ) : (
            <Link to="/user-dashboard" className="btn-success">
              {t.goToOrders}
            </Link>
          )}
          <Link to="/" className="btn-secondary">
            {t.backToHome}
          </Link>
        </div>
      </div>
    </div>
  );
}
