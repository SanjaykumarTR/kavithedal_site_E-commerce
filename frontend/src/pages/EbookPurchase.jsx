import { useState, useEffect, useContext } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";
import { mediaUrl } from "../utils/mediaUrl";
import "../styles/bookDetail.css";

export default function EbookPurchase() {
  const { id } = useParams();
  const { language } = useContext(LanguageContext);
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showConfirmation, setShowConfirmation] = useState(false);
  
  const [formData, setFormData] = useState({
    user_name: "",
    email: "",
    phone: "",
    address: ""
  });
  
  const translations = {
    en: {
      title: "eBook Purchase",
      bookDetails: "Book Details",
      fullName: "Full Name",
      email: "Email Address",
      phone: "Phone Number",
      address: "Contact Address",
      proceedToPay: "Proceed to Pay",
      price: "Price",
      processing: "Processing...",
      bookNotFound: "Book not found",
      loginRequired: "Please login to purchase eBooks",
      alreadyOwned: "You already own this eBook",
      purchaseSuccess: "Purchase Successful!",
      backToHome: "Back to Home",
      goToLibrary: "Go to Library",
      confirmPurchase: "Confirm Your Purchase?",
      confirmMessage: "Do you want to purchase this eBook for ₹{{price}}?",
      confirmYes: "Yes, Purchase",
      confirmNo: "No"
    },
    ta: {
      title: "இ-புத்தகம் வாங்குதல்",
      bookDetails: "புத்தக விவரங்கள்",
      fullName: "முழு பெயர்",
      email: "மின்னஞ்சல் முகவரி",
      phone: "தொலைபேசி எண்",
      address: "தொடர்பு முகவரி",
      proceedToPay: "பணம் செலுத்து",
      price: "விலை",
      processing: "செயலாக்குகிறது...",
      bookNotFound: "புத்தகம் கிடைக்கவில்லை",
      loginRequired: "இ-புத்தகங்களை வாங்க உள்நுழையவும்",
      alreadyOwned: "இந்த இ-புத்தகத்தை ஏற்கனவு வாங்கி விட்டீர்கள்",
      purchaseSuccess: "வாங்கியது வெற்றியாக உள்ளது!",
      backToHome: "முகப்பு பக்கம்",
      goToLibrary: "நூலகத்திற்கு செல்",
      confirmPurchase: "நீங்கள் வாங்க விரும்புகிறீர்களா?",
      confirmMessage: "இந்த இ-புத்தகத்தை ₹{{price}}க்கு வாங்க விரும்புகிறீர்களா?",
      confirmYes: "ஆம், வாங்கு",
      confirmNo: "இல்லை"
    }
  };
  
  const t = translations[language];
  
  useEffect(() => {
    fetchBook();
  }, [id]);
  
  useEffect(() => {
    // Pre-fill user data if logged in
    if (user) {
      setFormData(prev => ({
        ...prev,
        user_name: user.name || "",
        email: user.email || ""
      }));
    }
  }, [user]);
  
  const fetchBook = async () => {
    try {
      const response = await api.get(`/api/books/${id}/`);
      setBook(response.data);
    } catch (error) {
      console.error("Failed to fetch book:", error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!user) {
      navigate("/login");
      return;
    }
    
    // Show confirmation dialog
    setShowConfirmation(true);
  };
  
  const handleConfirmPurchase = async () => {
    setShowConfirmation(false);
    setSubmitting(true);
    setError("");
    
    try {
      // Create purchase with Razorpay integration
      const response = await api.post("/api/orders/ebook-purchase/", {
        book_id: id,
        user_name: formData.user_name,
        email: formData.email,
        phone: formData.phone,
        address: formData.address
      });
      
      const data = response.data;
      
      // If payment is completed (simulated mode), redirect to success
      if (data.status === "completed") {
        navigate(`/purchase-success?purchase_id=${data.purchase_id}&book=${data.book_title}`);
        return;
      }
      
      // If Razorpay order was created, initialize payment
      if (data.razorpay_order_id) {
        if (!window.Razorpay) {
          setError("Payment gateway is still loading. Please wait a moment and try again.");
          return;
        }

        const razorpayOptions = {
          key: data.razorpay_key_id,
          amount: data.amount * 100, // Convert to paise
          currency: data.currency,
          name: "Kavithedal Publications",
          description: `Purchase: ${data.book_title}`,
          order_id: data.razorpay_order_id,
          handler: async (paymentResponse) => {
            // Verify payment
            try {
              await api.post("/api/orders/verify-ebook-payment/", {
                purchase_id: data.purchase_id,
                razorpay_payment_id: paymentResponse.razorpay_payment_id,
                razorpay_signature: paymentResponse.razorpay_signature,
                razorpay_order_id: data.razorpay_order_id
              });
              navigate(`/purchase-success?purchase_id=${data.purchase_id}&book=${data.book_title}`);
            } catch {
              setError("Payment verification failed. Please contact support.");
            }
          },
          modal: {
            ondismiss: () => {
              setError("Payment was cancelled. Please try again.");
            }
          },
          prefill: {
            name: formData.user_name,
            email: formData.email,
            contact: formData.phone
          },
          theme: {
            color: "#B71C1C"
          }
        };

        const rzp = new window.Razorpay(razorpayOptions);
        rzp.open();
      }

    } catch (error) {
      console.error("Purchase error:", error);
      setError(error.response?.data?.error || "Failed to process purchase");
    } finally {
      setSubmitting(false);
    }
  };
  
  if (loading || authLoading) {
    return (
      <div className="book-detail-loading">
        <div className="spinner"></div>
      </div>
    );
  }
  
  if (!book) {
    return (
      <div className="book-detail-error">
        <h2>{t.bookNotFound}</h2>
        <Link to="/books">{language === "en" ? "Back to Books" : "புத்தகங்களுக்கு திரும்பு"}</Link>
      </div>
    );
  }
  
  return (
    <div className="ebook-purchase-page">
      <div className="purchase-container">
        <div className="purchase-left">
          <h1>{t.title}</h1>
          
          <div className="book-summary">
            <img src={mediaUrl(book.cover_image)} alt={book.title} />
            <div className="book-info">
              <h3>{book.title}</h3>
              <p>{book.author_name || book.author?.name}</p>
              <p className="price-label">{t.price}: ₹{book.ebook_price}</p>
            </div>
          </div>
        </div>
        
        <div className="purchase-right">
          <h2>{t.bookDetails}</h2>
          
          <form onSubmit={handleSubmit} className="purchase-form">
            <div className="form-group">
              <label>{t.fullName}</label>
              <input
                type="text"
                name="user_name"
                value={formData.user_name}
                onChange={handleChange}
                required
              />
            </div>
            
            <div className="form-group">
              <label>{t.email}</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
            
            <div className="form-group">
              <label>{t.phone}</label>
              <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                required
              />
            </div>
            
            <div className="form-group">
              <label>{t.address}</label>
              <textarea
                name="address"
                value={formData.address}
                onChange={handleChange}
                required
                rows="3"
              />
            </div>
            
            {error && <p className="error-message">{error}</p>}
            
            <button 
              type="submit" 
              className="btn-proceed"
              disabled={submitting}
            >
              {submitting ? t.processing : t.proceedToPay}
            </button>
          </form>
        </div>
      </div>
      
      {/* Confirmation Modal */}
      {showConfirmation && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>{t.confirmPurchase}</h3>
            <p>{t.confirmMessage.replace('{{price}}', book?.ebook_price)}</p>
            <div className="modal-buttons">
              <button 
                className="btn-confirm"
                onClick={handleConfirmPurchase}
                disabled={submitting}
              >
                {t.confirmYes}
              </button>
              <button 
                className="btn-cancel"
                onClick={() => setShowConfirmation(false)}
                disabled={submitting}
              >
                {t.confirmNo}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
