import { useState, useEffect, useContext } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";
import { CartContext } from "../context/CartContext";
import { WishlistContext } from "../context/WishlistContext";
import api from "../api/axios";
import { checkBookAccess } from "../api/orders";
import { mediaUrl } from "../utils/mediaUrl";
import PurchaseTypeSelector from "../components/PurchaseTypeSelector";
import "../styles/bookDetail.css";

export default function BookDetail() {
  const { id } = useParams();
  const { language } = useContext(LanguageContext);
  const { user } = useAuth();
  const { addToCart } = useContext(CartContext);
  const { toggleWishlist, isInWishlist } = useContext(WishlistContext);
  const navigate = useNavigate();

  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);
  const [showPurchaseSelector, setShowPurchaseSelector] = useState(false);
  const [toast, setToast] = useState("");

  const translations = {
    en: {
      by: "by",
      pages: "pages",
      language: "Language",
      description: "Description",
      buyNow: "Buy Now",
      readNow: "Read Now",
      addToCart: "Add to Cart",
      addToWishlist: "Add to Wishlist",
      removeFromWishlist: "Remove from Wishlist",
      addedToWishlist: "Added to wishlist!",
      removedFromWishlist: "Removed from wishlist.",
      alreadyOwned: "You already own this book",
      bookNotFound: "Book not found",
      ebook: "eBook",
      physical: "Physical Book",
      price: "Price",
      off: "OFF",
    },
    ta: {
      by: "வழங்கிய",
      pages: "பக்கங்கள்",
      language: "மொழி",
      description: "விளக்கம்",
      buyNow: "இப்போது வாங்கு",
      readNow: "இப்போது படி",
      addToCart: "கார்ட்டில் சேர்",
      addToWishlist: "விருப்பத்தில் சேர்",
      removeFromWishlist: "விருப்பத்திலிருந்து நீக்கு",
      addedToWishlist: "விருப்பப்பட்டியலில் சேர்க்கப்பட்டது!",
      removedFromWishlist: "விருப்பப்பட்டியலில் இருந்து நீக்கப்பட்டது.",
      alreadyOwned: "இந்த புத்தகத்தை ஏற்கனவு வாங்கி விட்டீர்கள்",
      bookNotFound: "புத்தகம் கிடைக்கவில்லை",
      ebook: "இ-புத்தகம்",
      physical: "இயல்பான புத்தகம்",
      price: "விலை",
      off: "தள்ளுபடி",
    }
  };

  const t = translations[language];

  useEffect(() => {
    fetchBook();
  }, [id]);

  useEffect(() => {
    if (user && book) {
      checkAccess();
    }
  }, [user, book]);

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

  const checkAccess = async () => {
    try {
      const response = await checkBookAccess(id);
      setHasAccess(response.has_access);
    } catch (error) {
      console.error("Failed to check access:", error);
    }
  };

  const handleBuyNow = () => {
    if (!user) {
      navigate("/login");
      return;
    }
    setShowPurchaseSelector(true);
  };

  const handleAddToCart = () => {
    if (!user) {
      alert(language === "en" ? "Please login to add items to your cart" : "கார்ட்டில் சேர்க்க உள்நுழையவும்");
      navigate("/login");
      return;
    }
    addToCart(book);
    alert(language === "en" ? "Added to cart!" : "கார்ட்டில் சேர்க்கப்பட்டது!");
  };

  const handleWishlist = () => {
    if (!user) {
      navigate("/login");
      return;
    }
    const removing = isInWishlist(book.id);
    toggleWishlist(book);
    const msg = removing ? t.removedFromWishlist : t.addedToWishlist;
    setToast(msg);
    setTimeout(() => setToast(""), 2500);
  };

  if (loading) {
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

  const hasDiscount = book.discount_percentage > 0;
  const physicalPrice = book.physical_price || book.price;
  const discountedPhysicalPrice = book.physical_final_price || physicalPrice;
  const discountedEbookPrice = book.ebook_final_price || book.ebook_price;

  return (
    <div className="book-detail-page">
      <div className="book-detail-container">
        <div className="book-detail-left">
          {hasDiscount && (
            <span className="book-discount-badge">-{book.discount_percentage}% {t.off}</span>
          )}
          <img
            src={mediaUrl(book.cover_image)}
            alt={book.title}
            className="book-detail-cover"
          />
        </div>

        <div className="book-detail-right">
          <h1 className="book-detail-title">{book.title}</h1>
          <p className="book-detail-author">
            {t.by} {book.author_name || book.author?.name}
          </p>

          <div className="book-detail-meta">
            {book.pages > 0 && <span>{book.pages} {t.pages}</span>}
            <span>{book.language}</span>
          </div>

          {/* Price display */}
          <div className="book-price-info">
            {book.ebook_price > 0 && (
              <div className="price-row">
                <span className="price-type">{t.ebook}:</span>
                {hasDiscount ? (
                  <>
                    <span className="price-original">₹{book.ebook_price}</span>
                    <span className="price-final">₹{discountedEbookPrice}</span>
                  </>
                ) : (
                  <span className="price-final">₹{book.ebook_price}</span>
                )}
              </div>
            )}
            {physicalPrice > 0 && (
              <div className="price-row">
                <span className="price-type">{t.physical}:</span>
                {hasDiscount ? (
                  <>
                    <span className="price-original">₹{physicalPrice}</span>
                    <span className="price-final">₹{discountedPhysicalPrice}</span>
                  </>
                ) : (
                  <span className="price-final">₹{physicalPrice}</span>
                )}
              </div>
            )}
          </div>

          {toast && <div className="book-detail-toast">{toast}</div>}

          {hasAccess ? (
            <div className="book-owned-section">
              <p className="owned-message">{t.alreadyOwned}</p>
              <Link to={`/reader/${book.id}`} className="btn-read-now">
                {t.readNow}
              </Link>
            </div>
          ) : (
            <div className="book-action-buttons">
              <button className="btn-buy-now" onClick={handleBuyNow}>
                {t.buyNow}
              </button>
              <button className="btn-add-cart" onClick={handleAddToCart}>
                {t.addToCart}
              </button>
              <button
                className={`btn-wishlist${isInWishlist(book.id) ? " active" : ""}`}
                onClick={handleWishlist}
                title={isInWishlist(book.id) ? t.removeFromWishlist : t.addToWishlist}
              >
                {isInWishlist(book.id) ? "❤️" : "🤍"}
                {" "}{isInWishlist(book.id) ? t.removeFromWishlist : t.addToWishlist}
              </button>
            </div>
          )}

          <div className="book-description">
            <h3>{t.description}</h3>
            <p>{book.description}</p>
          </div>
        </div>
      </div>

      {/* Purchase type selector modal */}
      {showPurchaseSelector && (
        <PurchaseTypeSelector
          book={book}
          onClose={() => setShowPurchaseSelector(false)}
        />
      )}
    </div>
  );
}
