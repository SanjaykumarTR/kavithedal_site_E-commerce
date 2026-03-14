import { useState, useEffect, useContext } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";
import { getSecurePdfUrl } from "../api/orders";
import "../styles/reader.css";

export default function Reader() {
  const { id } = useParams();
  const { language } = useContext(LanguageContext);
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pdfUrl, setPdfUrl] = useState(null);
  
  const translations = {
    en: {
      loading: "Loading your book...",
      error: "Unable to load book",
      notPurchased: "You have not purchased this book",
      backToLibrary: "Back to Library",
      page: "Page",
      of: "of",
      accessDenied: "Access Denied",
      purchaseToRead: "Please purchase this book to read it"
    },
    ta: {
      loading: "உங்கள் புத்தகத்தை ஏற்றுகிறது...",
      error: "புத்தகத்தை ஏற்ற முடியவில்லை",
      notPurchased: "இந்த புத்தகத்தை வாங்கவில்லை",
      backToLibrary: "லைப்ரரிக்கு திரும்பு",
      page: "பக்கம்",
      of: "இல்",
      accessDenied: "அணுகல் மறுக்கப்பட்டது",
      purchaseToRead: "இந்த புத்தகத்தைப் படிப்பதற்கு வாங்கவும்"
    }
  };
  
  const t = translations[language];
  
  useEffect(() => {
    fetchBookAndAccess();
    
    // Disable right-click context menu
    const handleContextMenu = (e) => {
      e.preventDefault();
    };
    
    // Disable keyboard shortcuts for printing and saving
    const handleKeyDown = (e) => {
      // Ctrl+P (Print)
      if (e.ctrlKey && e.key === 'p') {
        e.preventDefault();
      }
      // Ctrl+S (Save)
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
      }
      // Ctrl+U (View Source)
      if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
      }
      // Ctrl+Shift+I (Developer Tools)
      if (e.ctrlKey && e.shiftKey && e.key === 'I') {
        e.preventDefault();
      }
      // F12 (Developer Tools)
      if (e.key === 'F12') {
        e.preventDefault();
      }
    };
    
    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [id, user]);
  
  const fetchBookAndAccess = async () => {
    if (!user) {
      navigate("/login");
      return;
    }
    
    try {
      // First check if user has purchased the book
      const accessResponse = await api.get(`/api/books/${id}/check-access/`);
      
      if (!accessResponse.data.has_access) {
        setError(t.purchaseToRead);
        setLoading(false);
        return;
      }
      
      // Check if book has PDF
      const bookResponse = await api.get(`/api/books/${id}/`);
      const bookData = bookResponse.data;
      
      if (!bookData.pdf_file) {
        setError("No PDF file available for this book");
        setLoading(false);
        return;
      }
      
      setBook(bookData);
      
      // Fetch the secure Cloudinary PDF URL from the backend
      try {
        const pdfResponse = await api.get(`/api/books/${id}/pdf/`);
        const url = pdfResponse.data.pdf_url;
        if (!url) {
          setError("PDF URL not available for this book");
          setLoading(false);
          return;
        }
        setPdfUrl(url);
      } catch (pdfError) {
        console.error("Failed to get PDF URL:", pdfError);
        setError(pdfError.response?.data?.error || "Failed to load PDF. Please try again.");
      }
      
    } catch (err) {
      console.error("Error loading book:", err);
      if (err.response?.status === 403 || err.response?.status === 401) {
        setError(t.purchaseToRead);
      } else {
        setError(t.error);
      }
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <div className="reader-loading">
        <div className="spinner"></div>
        <p>{t.loading}</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="reader-error">
        <div className="error-icon">🔒</div>
        <h2>{t.accessDenied}</h2>
        <p>{error}</p>
        <Link to="/library" className="btn-back">
          {t.backToLibrary}
        </Link>
      </div>
    );
  }
  
  return (
    <div 
      className="reader-page"
      onContextMenu={(e) => e.preventDefault()}
    >
      <div className="reader-header">
        <Link to="/library" className="btn-back">
          ← {t.backToLibrary}
        </Link>
        <h1 className="reader-title">{book?.title}</h1>
        <div className="reader-watermark">
          {user?.email}
        </div>
      </div>
      
      <div className="reader-container">
        {pdfUrl && (
          <>
            <div className="reader-pdf-actions">
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-open-pdf"
              >
                Open PDF in New Tab
              </a>
              <a
                href={pdfUrl}
                download={book?.title ? `${book.title}.pdf` : "book.pdf"}
                className="btn-download-pdf"
              >
                Download PDF
              </a>
            </div>
            <iframe
              src={pdfUrl}
              className="pdf-viewer"
              title={book?.title}
              onContextMenu={(e) => e.preventDefault()}
            />
          </>
        )}
      </div>
      
      <div className="reader-footer">
        <p>{book?.title} - {t.page} 1 {t.of} 1</p>
        <p className="reader-protected">🔒 Protected Content</p>
      </div>
    </div>
  );
}
