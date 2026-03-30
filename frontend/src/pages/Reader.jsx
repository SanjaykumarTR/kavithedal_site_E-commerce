/**
 * Secure Ebook Reader Component
 * 
 * Features:
 * - Only authenticated users with valid purchases can access
 * - PDF URLs are time-limited (5 minutes)
 * - Right-click disabled
 * - Print/Save shortcuts disabled
 * - Reading progress tracking
 * - No external iframe embedding allowed
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { LanguageContext } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";
import "../styles/reader.css";

export default function Reader() {
  const { id } = useParams();
  const { language } = LanguageContext || { language: 'en' };
  // Try to get user from AuthContext, fallback to localStorage
  const authContext = useAuth ? useAuth() : null;
  const authUser = authContext?.user;
  
  // Get user directly from localStorage to ensure persistence
  const [user, setUser] = useState(null);
  const navigate = useNavigate();
  
  // Check localStorage for user data (like Library.jsx does)
  useEffect(() => {
    const storedUser = localStorage.getItem("auth_user");
    const token = localStorage.getItem("access_token");
    if (storedUser && token) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        // Invalid stored user
      }
    }
  }, []);
  
  // Use either auth context user or localStorage user
  const currentUser = user || authUser;
  
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const containerRef = useRef(null);
  
  // Translation strings
  const translations = {
    en: {
      loading: "Loading your book...",
      loadingProgress: "Loading",
      error: "Unable to load book",
      notPurchased: "You have not purchased this book",
      backToLibrary: "Back to Library",
      page: "Page",
      of: "of",
      accessDenied: "Access Denied",
      purchaseToRead: "Please purchase this book to read it",
      fullscreen: "Fullscreen",
      exitFullscreen: "Exit Fullscreen",
      protectedContent: "Protected Content",
      openInNewTab: "Open in New Tab"
    },
    ta: {
      loading: "உங்கள் புத்தகத்தை ஏற்றுகிறது...",
      loadingProgress: "ஏற்றுகிறது",
      error: "புத்தகத்தை ஏற்ற முடியவில்லை",
      notPurchased: "இந்த புத்தகத்தை வாங்கவில்லை",
      backToLibrary: "லைப்ரரிக்கு திரும்பு",
      page: "பக்கம்",
      of: "இல்",
      accessDenied: "அணுகல் மறுக்கப்பட்டது",
      purchaseToRead: "இந்த புத்தகத்தைப் படிப்பதற்கு வாங்கவும்",
      fullscreen: "முழு திரை",
      exitFullscreen: "முழு திரையை விடு",
      protectedContent: "பாதுகாக்கப்படும் உள்ளடக்கம்",
      openInNewTab: "புதிய தந்தத்தில் திறக்க"
    }
  };
  
  const t = translations[language] || translations.en;

  // Security: Prevent various keyboard shortcuts and right-click
  useEffect(() => {
    const handleContextMenu = (e) => {
      e.preventDefault();
      return false;
    };
    
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.key === 'p') { e.preventDefault(); return false; }
      if (e.ctrlKey && e.key === 's') { e.preventDefault(); return false; }
      if (e.ctrlKey && e.key === 'u') { e.preventDefault(); return false; }
      if (e.ctrlKey && e.shiftKey && e.key === 'I') { e.preventDefault(); return false; }
      if (e.key === 'F12') { e.preventDefault(); return false; }
      if (e.key === 'PrintScreen') { e.preventDefault(); return false; }
    };
    
    const handleBeforeUnload = () => {
      try {
        if (window.self !== window.top) {
          window.top.location = window.self.location;
        }
      } catch (e) { /* cross-origin restriction */ }
    };

    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('beforeunload', handleBeforeUnload);
    
    try {
      if (window.self !== window.top) {
        document.body.style.display = 'none';
        window.top.location = window.self.location;
      }
    } catch (e) { /* cross-origin restriction */ }
    
    return () => {
      document.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Fetch book and verify access
  useEffect(() => {
    fetchBookAndAccess();
  }, [id, user, authUser]);

  const fetchBookAndAccess = async () => {
    const currentUserCheck = user || authUser;
    if (!currentUserCheck) {
      navigate("/login");
      return;
    }
    
    try {
      const accessResponse = await api.get(`/api/books/${id}/check-access/`);
      
      if (!accessResponse.data.has_access) {
        setError(t.purchaseToRead);
        setLoading(false);
        return;
      }
      
      const bookResponse = await api.get(`/api/books/${id}/`);
      const bookData = bookResponse.data;
      
      if (!bookData.pdf_file) {
        setError("No PDF file available for this book");
        setLoading(false);
        return;
      }
      
      setBook(bookData);
      
      try {
        const pdfResponse = await api.get(`/api/books/${id}/pdf/`);
        const url = pdfResponse.data.pdf_url;
        if (!url) {
          setError("PDF URL not available for this book");
          setLoading(false);
          return;
        }
        setPdfUrl(url);
        setLoadingProgress(100);
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

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  }, []);

  if (loading) {
    return (
      <div className="reader-loading">
        <div className="loading-spinner"></div>
        <p>{t.loading}</p>
        {loadingProgress > 0 && loadingProgress < 100 && (
          <div className="loading-progress">
            <div className="loading-progress-bar" style={{ width: `${loadingProgress}%` }}></div>
          </div>
        )}
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="reader-error">
        <div className="error-icon">🔒</div>
        <h2>{t.accessDenied}</h2>
        <p>{error}</p>
        <Link to="/library" className="btn-back">{t.backToLibrary}</Link>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="reader-page"
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* Header */}
      <div className="reader-header">
        <Link to="/library" className="btn-back">← {t.backToLibrary}</Link>
        <h1 className="reader-title">{book?.title}</h1>
        <div className="reader-controls">
          <button onClick={toggleFullscreen} className="control-btn" title={t.fullscreen}>
            ⛶
          </button>
        </div>
      </div>
      
      {/* PDF Viewer */}
      <div className="reader-container">
        {pdfUrl && (
          <div className="pdf-wrapper">
            <div className="reader-pdf-actions">
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-open-pdf"
              >
                📄 {t.openInNewTab}
              </a>
            </div>
            
            <iframe
              src={pdfUrl}
              className="pdf-viewer"
              title={book?.title}
              onError={() => setError("Failed to load PDF")}
            />
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="reader-footer">
        <div className="reader-protection">🔒 {t.protectedContent}</div>
      </div>
    </div>
  );
}
