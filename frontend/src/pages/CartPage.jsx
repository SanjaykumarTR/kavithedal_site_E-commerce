import { useContext, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CartContext } from "../context/CartContext";
import { LanguageContext } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";
import { createCartCheckout, initiateCashfreeCheckout } from "../api/orders";
import "../styles/cart.css";

export default function CartPage() {
  const { cart, removeFromCart, updateQuantity, cartCount } = useContext(CartContext);
  const { language } = useContext(LanguageContext);
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const subtotal =
    Math.round(cart.reduce((sum, item) => sum + item.price * item.qty, 0) * 100) / 100;

  // Delivery charge applies only to physical books
  const physicalSubtotal =
    Math.round(
      cart
        .filter((item) => item.book_type !== "ebook")
        .reduce((sum, item) => sum + item.price * item.qty, 0) * 100
    ) / 100;

  function calcDeliveryCharge(total) {
    if (total <= 0) return 0;
    if (total < 500) return 40;
    if (total < 1000) return 30;
    return 20;
  }

  const deliveryCharge = calcDeliveryCharge(physicalSubtotal);
  const total = Math.round((subtotal + deliveryCharge) * 100) / 100;

  const handlePayment = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      alert(language === "en" ? "Please login to purchase" : "Login to purchase");
      navigate("/login");
      return;
    }
    if (cart.length === 0) {
      alert(language === "en" ? "Your cart is empty" : "Cart is empty");
      return;
    }

    setLoading(true);
    try {
      const itemsForBackend = cart.map((item) => ({
        book_id: item.id,
        qty: item.qty,
        price: item.price,
        book_type: item.book_type || "physical",
        title: item.title || "",
      }));

      const data = await createCartCheckout(
        itemsForBackend,
        total,
        user?.phone || ""
      );

// Simulation mode (no Cashfree configured on backend)
        if (data.status === "completed") {
          cart.forEach((item) => removeFromCart(item.id));
          navigate("/user-dashboard");
          return;
        }

        // Production — redirect to Cashfree
        if (data.payment_session_id) {
          // Cart is cleared on the success page after verification
          initiateCashfreeCheckout(data);
          return;
        }

      alert(language === "en" ? "Payment initiation failed" : "Payment failed");
    } catch (err) {
      console.error("Cart payment error:", err);
      const msg =
        err.response?.data?.error ||
        (language === "en" ? "Failed to initiate payment" : "Payment failed");
      alert(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="cart-page">
      <div className="cart-header">
        <h2 className="page-title">
          {language === "en" ? "Your Cart" : "Your Cart"}
        </h2>
        {cart.length > 0 && (
          <p className="cart-count">
            {cartCount} {language === "en" ? "item(s)" : "items"}
          </p>
        )}
      </div>

      {cart.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">Cart</div>
          <h3>{language === "en" ? "Your cart is empty" : "Cart is empty"}</h3>
          <p>{language === "en" ? "Add some books to your cart" : "Add books to cart"}</p>
          <Link to="/books" className="browse-btn">
            {language === "en" ? "Browse Books" : "Browse"}
          </Link>
        </div>
      ) : (
        <div className="cart-layout">
          {/* ── Cart items ──────────────────────────────────────────────────── */}
          <div className="cart-items-section">
            <h3 className="section-label">
              {language === "en" ? "Items in Cart" : "Cart Items"}
            </h3>
            {cart.map((item) => (
              <div key={item.id} className="cart-item-card">
                <img
                  src={
                    item.image ||
                    "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=200&h=300&fit=crop"
                  }
                  alt={item.title}
                  className="ci-img"
                />
                <div className="ci-details">
                  <h4 className="ci-title">{item.title}</h4>
                  <p className="ci-author">{item.author}</p>
                  <span className="ci-category">{item.category}</span>
                  <div className="ci-price-row">
                    <span className="ci-price">Rs.{item.price.toFixed(2)}</span>
                    <span className="ci-old-price">Rs.{item.oldPrice.toFixed(2)}</span>
                    <span className="ci-discount">-{item.discount}%</span>
                  </div>
                  <div className="ci-qty-row">
                    <span className="ci-qty-label">
                      {language === "en" ? "Qty" : "Qty"}:
                    </span>
                    <div className="ci-qty-controls">
                      <button
                        className="qty-btn"
                        onClick={() => updateQuantity(item.id, item.qty - 1)}
                      >
                        -
                      </button>
                      <span className="ci-qty">{item.qty}</span>
                      <button
                        className="qty-btn"
                        onClick={() => updateQuantity(item.id, item.qty + 1)}
                      >
                        +
                      </button>
                    </div>
                    <span className="ci-subtotal">
                      = Rs.{(item.price * item.qty).toFixed(2)}
                    </span>
                  </div>
                </div>
                <button
                  className="ci-remove-btn"
                  onClick={() => removeFromCart(item.id)}
                  title={language === "en" ? "Remove" : "Remove"}
                >
                  X
                </button>
              </div>
            ))}
          </div>

          {/* ── Order summary ────────────────────────────────────────────────── */}
          <div className="cart-summary">
            <h3 className="summary-title">
              {language === "en" ? "Order Summary" : "Summary"}
            </h3>

            <div className="summary-row">
              <span>{language === "en" ? "Books Total" : "புத்தகங்கள் மொத்தம்"}</span>
              <span>₹{subtotal.toFixed(2)}</span>
            </div>

            <div className="summary-row">
              <span>{language === "en" ? "Delivery Charge" : "டெலிவரி கட்டணம்"}</span>
              <span className={deliveryCharge === 0 ? "free-tag" : ""}>
                {deliveryCharge === 0
                  ? language === "en"
                    ? "FREE"
                    : "இலவசம்"
                  : "₹" + deliveryCharge}
              </span>
            </div>

            {physicalSubtotal > 0 && (
              <p className="free-ship-note">
                {physicalSubtotal < 500
                  ? language === "en"
                    ? `Add ₹${(500 - physicalSubtotal).toFixed(2)} more to reduce delivery to ₹30`
                    : `₹30 டெலிவரிக்கு ₹${(500 - physicalSubtotal).toFixed(2)} மேலும் சேர்க்கவும்`
                  : physicalSubtotal < 1000
                  ? language === "en"
                    ? `Add ₹${(1000 - physicalSubtotal).toFixed(2)} more to reduce delivery to ₹20`
                    : `₹20 டெலிவரிக்கு ₹${(1000 - physicalSubtotal).toFixed(2)} மேலும் சேர்க்கவும்`
                  : null}
              </p>
            )}

            <div className="summary-divider"></div>

            <div className="summary-total-row">
              <span className="total-label">
                {language === "en" ? "Final Total" : "இறுதி மொத்தம்"}
              </span>
              <span className="total-amount">₹{total.toFixed(2)}</span>
            </div>

            <button
              className="pay-now-btn"
              onClick={handlePayment}
              disabled={loading}
            >
{loading
                  ? language === "en"
                    ? "Redirecting..."
                    : "திருப்பிவிடுகிறது..."
                  : language === "en"
                  ? "Pay Now with Cashfree"
                  : "Cashfree மூலம் பணம் செலுத்து"}
            </button>

<div className="payment-info">
                <span className="secure-icon">🔒</span>
                <span>100% Secure Payment via Cashfree</span>
              </div>

            <div className="payment-methods">
              <span>UPI</span>
              <span>Cards</span>
              <span>NetBanking</span>
              <span>Wallets</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
