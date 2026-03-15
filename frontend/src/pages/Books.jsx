import { useState, useContext, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import ProductCard from "../components/ProductCard";
import api from "../api/axios";
import "../styles/books.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Books() {
  const { language } = useContext(LanguageContext);
  const [searchParams] = useSearchParams();

  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [maxPrice, setMaxPrice] = useState(2000);
  const [search] = useState(searchParams.get("search") || "");
  const [selectedCategory, setSelectedCategory] = useState(
    searchParams.get("category") || "all"
  );

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        const response = await api.get("/api/books/");
        const booksData = response.data.results || response.data;
        setBooks(booksData);
      } catch (err) {
        console.error("Error fetching books:", err);
        setError("Failed to load books");
      } finally {
        setLoading(false);
      }
    };
    fetchBooks();
  }, []);

  // Get unique categories from books
  const categories = [...new Set(books.map((book) => book.category_name).filter(Boolean))];

  // Map backend data to frontend format
  const mappedBooks = books.map((book) => {
    const originalPrice = Number(book.price) || 0;
    const discountPercent = Number(book.discount_percentage) || 0;
    const discountedPrice = discountPercent > 0 
      ? originalPrice - (originalPrice * discountPercent / 100) 
      : originalPrice;
    
    // Get ebook and physical prices from API
    const ebookPrice = book.ebook_price ? Number(book.ebook_price) : null;
    const physicalPrice = book.physical_price ? Number(book.physical_price) : null;
    const ebookFinalPrice = book.ebook_final_price ? Number(book.ebook_final_price) : null;
    const physicalFinalPrice = book.physical_final_price ? Number(book.physical_final_price) : null;

    return {
      id: book.id,
      title: book.title,
      author: book.author_name || book.author?.name || "Unknown Author",
      price: discountPercent > 0 ? discountedPrice : originalPrice,
      oldPrice: originalPrice,
      discount: discountPercent,
      rating: 4.5,
      image: book.cover_image
        ? (book.cover_image.startsWith("http") ? book.cover_image : `${API_BASE}${book.cover_image}`)
        : "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=200&h=300&fit=crop",
      category: book.category_name || "Uncategorized",
      ebook_price: ebookPrice,
      physical_price: physicalPrice,
      ebook_final_price: ebookFinalPrice,
      physical_final_price: physicalFinalPrice,
      discount_percentage: discountPercent
    };
  });

  const filteredBooks = mappedBooks.filter((book) => {
    // Show all books - removed price filter
    const matchesSearch =
      book.title.toLowerCase().includes(search.toLowerCase()) ||
      (book.author?.name || book.author || "").toLowerCase().includes(search.toLowerCase());
    
    // Category filter
    const matchesCategory =
      selectedCategory === "all" || 
      (book.category && book.category.toLowerCase() === selectedCategory.toLowerCase());
    
    // Price filter - filter by discounted price
    const matchesPrice = book.price <= maxPrice;
    
    return matchesSearch && matchesCategory && matchesPrice;
  });

  return (
    <div className="books-layout">
      {/* FILTER SIDEBAR */}
      <div className="filters">
        <h3>{language === "en" ? "Categories" : "வகைகள்"}</h3>

        {/* CATEGORIES */}
        <div className="filter-group">
          <label>{language === "en" ? "Choose Category" : "தேர்வு செய்"}</label>
          <div className="category-options">
            <button
              className={`category-chip ${selectedCategory === "all" ? "active" : ""}`}
              onClick={() => setSelectedCategory("all")}
            >
              {language === "en" ? "All" : "அனைத்தும்"}
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                className={`category-chip ${selectedCategory === cat ? "active" : ""}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* PRICE RANGE */}
        <div className="filter-group">
          <label>
            {language === "en" ? "Price Range" : "விலை வரம்பு"}: ₹{maxPrice}
          </label>
          <input
            type="range"
            min="100"
            max="2000"
            value={maxPrice}
            onChange={(e) => setMaxPrice(Number(e.target.value))}
          />
          <div className="price-range-labels">
            <span>₹100</span>
            <span>₹2000</span>
          </div>
        </div>

        {/* SEARCH */}
        
      </div>

      {/* PRODUCT GRID */}
      <div className="products-section">
        <div className="products-header">
          <p className="results-count">
            {filteredBooks.length} {language === "en" ? "books found" : "நூல்கள் கிடைத்தன"}
          </p>
        </div>
        <div className="products-grid">
          {loading ? (
            <div className="loading">Loading books...</div>
          ) : error ? (
            <div className="error">{error}</div>
          ) : filteredBooks.length > 0 ? (
            filteredBooks.map((book) => (
              <ProductCard key={book.id} book={book} />
            ))
          ) : (
            <div className="no-results">
              <p>{language === "en" ? "No books found" : "நூல்கள் எதுவும் கிடைக்கவில்லை"}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
