import { useContext, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CartContext } from "../context/CartContext";
import { WishlistContext } from "../context/WishlistContext";
import { LanguageContext } from "../context/LanguageContext";
import PurchaseTypeSelector from "./PurchaseTypeSelector";
import "../styles/productCard.css";

export default function ProductCard({ book, showBothPrices = false }) {
  const { addToCart } = useContext(CartContext);
  const { toggleWishlist, isInWishlist } = useContext(WishlistContext);
  const { language } = useContext(LanguageContext);
  const navigate = useNavigate();
  const [purchasing, setPurchasing] = useState(false);
  const [showPurchaseType, setShowPurchaseType] = useState(false);
  const wished = isInWishlist(book.id);
  
  // Translations
  const translations = {
    en: {
      buyNow: "Buy Now",
      addToCart: "Add to Cart",
      addedToCart: "Added to cart!",
      addedToWishlist: "Added to wishlist!",
      removedFromWishlist: "Removed from wishlist!",
      loginToPurchase: "Please login to purchase books",
      purchaseSuccess: "Purchase successful!",
      addedToLibrary: "has been added to your library",
      ordered: "has been ordered",
      purchaseFailed: "Failed to purchase book",
      loginToDownload: "Please login to download the book",
      purchaseToDownload: "Please purchase the book to download",
      pdfNotAvailable: "PDF not available for this book",
      downloadStarted: "Download started!",
      downloadFailed: "Failed to download. Please try again."
    },
    ta: {
      buyNow: "இப்போது வாங்கு",
      addToCart: "கார்ட்டில் சேர்",
      addedToCart: "கார்ட்டில் சேர்க்கப்பட்டது!",
      addedToWishlist: "விஷ்லிஸ்ட்டில் சேர்க்கப்பட்டது!",
      removedFromWishlist: "விஷ்லிஸ்ட்டில் இருந்து நீக்கப்பட்டது!",
      loginToPurchase: "புத்தகங்களை வாங்க உள்நுழையவும்",
      purchaseSuccess: "வாங்கியது வெற்றியாக உள்ளது!",
      addedToLibrary: "உங்கள் நூலகத்தில் சேர்க்கப்பட்டது",
      ordered: "ஆணை வழங்கப்பட்டது",
      purchaseFailed: "புத்தகம் வாங்க முடியவில்லை",
      loginToDownload: "புத்தகத்தைப் பதிவிறக்க உள்நுழையவும்",
      purchaseToDownload: "பதிவிறக்க புத்தகத்தை வாங்கவும்",
      pdfNotAvailable: "இந்த புத்தகத்திற்கு PDF இல்லை",
      downloadStarted: "பதிவிறக்கம் தொடங்கியது!",
      downloadFailed: "பதிவிறக்கத்தில் தோல்வி. மீண்டும் முயற்சிக்கவும்."
    }
  };
  
  const t = translations[language];

  // Get prices - support both API response (ebook_price, physical_price) and local data (price)
  // Use book.price as fallback for physical price when not available
  const ebookPrice = book.ebook_price || book.price;
  const physicalPrice = book.physical_price || book.price;
  const hasEbook = book.ebook_price != null && book.ebook_price > 0;
  const hasPhysical = (book.physical_price != null && book.physical_price > 0) || book.price > 0;
  // Always show both prices when either ebook or physical is available
  const showBoth = hasEbook || hasPhysical;
  
  // Get discounted/final prices from API
  const ebookFinalPrice = book.ebook_final_price || ebookPrice;
  const physicalFinalPrice = book.physical_final_price || physicalPrice;
  const hasDiscount = book.discount_percentage > 0;

  const handleAddToCart = (e) => {
    e.preventDefault();
    e.stopPropagation();
    addToCart(book);
    alert(t.addedToCart);
  };

  const handleWishlist = (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggleWishlist(book);
    alert(wished ? t.removedFromWishlist : t.addedToWishlist);
  };

  const handleBuyNow = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    const token = localStorage.getItem("access_token");
    if (!token) {
      alert(t.loginToPurchase);
      navigate("/login");
      return;
    }
    
    // Show purchase type selector
    setShowPurchaseType(true);
  };

  return (
    <div className="product-card-wrapper">
      <Link to={`/book/${book.id}`} className="product-card">
        {/* Discount Badge */}
        {book.discount_percentage > 0 && (
          <div className="discount-badge">-{book.discount_percentage}%</div>
        )}

        <img
          src={book.image}
          alt={book.title}
          onError={(e) => {
            e.target.onerror = null;
            e.target.src = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=200&h=300&fit=crop";
          }}
        />

        <div className="product-info">
          <h4>{book.title}</h4>
          <p className="author">{book.author}</p>
          <p className="book-category-tag">{book.category}</p>

          <div className="price-row">
            {showBoth ? (
              <div className="dual-prices">
                {hasEbook && (
                  <div className="price-item">
                    <span className="price-type">eBook:</span>
                    {hasDiscount ? (
                      <>
                        <span className="price">₹{ebookFinalPrice}</span>
                        <span className="old-price">₹{ebookPrice}</span>
                      </>
                    ) : (
                      <span className="price">₹{ebookPrice}</span>
                    )}
                  </div>
                )}
                {hasPhysical && (
                  <div className="price-item">
                    <span className="price-type">Physical:</span>
                    {hasDiscount ? (
                      <>
                        <span className="price">₹{physicalFinalPrice}</span>
                        <span className="old-price">₹{physicalPrice}</span>
                      </>
                    ) : (
                      <span className="price">₹{physicalPrice}</span>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <>
                {hasDiscount ? (
                  <>
                    <span className="price">₹{physicalFinalPrice}</span>
                    <span className="old-price">₹{physicalPrice}</span>
                  </>
                ) : (
                  <span className="price">₹{physicalPrice}</span>
                )}
              </>
            )}
          </div>

          <div className="rating">
            {"⭐".repeat(Math.floor(book.rating))} ({book.rating})
          </div>
        </div>
      </Link>

      {/* Action buttons outside the Link */}
      <div className="card-actions">
        {/* Wishlist */}
        <div
          className={`wishlist ${wished ? "active" : ""}`}
          onClick={handleWishlist}
          title={wished ? "Remove from Wishlist" : "Add to Wishlist"}
        >
          ♥
        </div>
        <button className="buy-now-btn" onClick={handleBuyNow} disabled={purchasing}>
          {purchasing ? "..." : t.buyNow}
        </button>
        <button className="cart-btn" onClick={handleAddToCart}>
          {t.addToCart}
        </button>
      </div>

      {/* Purchase Type Selector Modal */}
      {showPurchaseType && (
        <PurchaseTypeSelector 
          book={book} 
          onClose={() => setShowPurchaseType(false)} 
        />
      )}
    </div>
  );
}
