import { createContext, useState, useEffect } from "react";
import { useAuth } from "./AuthContext";

export const CartContext = createContext();

// Build a user-specific storage key; null when no user (guest = no cart)
const getCartKey = (user) =>
  user ? `cart_${user.id || user.email}` : null;

const parseCart = (raw) => {
  try {
    const parsed = JSON.parse(raw);
    return (parsed || [])
      .map((item) => {
        if (!item || typeof item !== "object" || !item.id) return null;
        let authorName = "";
        if (item.author) {
          authorName =
            typeof item.author === "object"
              ? item.author?.name || ""
              : String(item.author);
        }
        return {
          ...item,
          id: String(item.id),
          title: String(item.title || ""),
          author: String(authorName),
          category: String(item.category || ""),
          image: String(item.image || ""),
          book_type: String(item.book_type || "physical"),
          qty: Number(item.qty) || 1,
          price: Number(item.price) || 0,
          oldPrice: Number(item.oldPrice) || 0,
          discount: Number(item.discount) || 0,
        };
      })
      .filter(Boolean);
  } catch {
    return [];
  }
};

const loadCart = (key) => {
  if (!key) return [];
  const saved = localStorage.getItem(key);
  return saved ? parseCart(saved) : [];
};

export const CartProvider = ({ children }) => {
  const { user } = useAuth();

  // Synchronous init: read auth_user directly from localStorage so the correct
  // cart is available on the very first render (before AuthContext's useEffect).
  const [cart, setCart] = useState(() => {
    try {
      const savedUser = localStorage.getItem("auth_user");
      const u = savedUser ? JSON.parse(savedUser) : null;
      return loadCart(getCartKey(u));
    } catch {
      return [];
    }
  });

  // When the user changes (login / logout / switch account) load that user's cart.
  useEffect(() => {
    setCart(loadCart(getCartKey(user)));
  }, [user]);

  // Persist cart under the user-specific key whenever it changes.
  // When user is null (logged out) we do NOT persist — the cart stays empty.
  useEffect(() => {
    const key = getCartKey(user);
    if (!key) return;
    try {
      localStorage.setItem(key, JSON.stringify(cart));
    } catch (e) {
      console.error("Error saving cart to localStorage:", e);
    }
  }, [cart, user]);

  const addToCart = (book) => {
    try {
      if (!book || !book.id || !book.title) {
        console.error("Invalid book object:", book);
        return;
      }
      setCart((prev) => {
        const exists = prev.find((item) => item.id === book.id);
        if (exists) {
          return prev.map((item) =>
            item.id === book.id ? { ...item, qty: item.qty + 1 } : item
          );
        }

        let price =
          parseFloat(book.ebook_price) ||
          parseFloat(book.price) ||
          parseFloat(book.physical_price) ||
          0;
        let oldPrice = price;
        let discount = 0;

        if (book.discount_percentage && book.discount_percentage > 0) {
          discount = parseFloat(book.discount_percentage);
          price = price - (price * discount) / 100;
        }

        let authorName = "";
        if (book.author) {
          authorName =
            typeof book.author === "object"
              ? book.author.name || ""
              : String(book.author);
        } else if (book.author_name) {
          authorName = book.author_name;
        } else if (book.authorName) {
          authorName = book.authorName;
        }

        return [
          ...prev,
          {
            id: String(book.id),
            title: String(book.title || ""),
            author: String(authorName),
            category: String(book.category || ""),
            image: String(book.image || book.cover_image || book.coverImage || ""),
            book_type: String(book.book_type || "physical"),
            qty: 1,
            price: Math.round(price * 100) / 100,
            oldPrice: Math.round(oldPrice * 100) / 100,
            discount: Math.round(discount * 100) / 100,
          },
        ];
      });
    } catch (error) {
      console.error("Error adding to cart:", error);
    }
  };

  const removeFromCart = (bookId) => {
    setCart((prev) => prev.filter((item) => item.id !== bookId));
  };

  const updateQuantity = (bookId, newQty) => {
    if (newQty < 1) {
      removeFromCart(bookId);
      return;
    }
    setCart((prev) =>
      prev.map((item) =>
        item.id === bookId ? { ...item, qty: newQty } : item
      )
    );
  };

  const clearCart = () => setCart([]);

  const cartCount = cart.reduce((sum, item) => sum + item.qty, 0);

  return (
    <CartContext.Provider
      value={{ cart, addToCart, removeFromCart, updateQuantity, clearCart, cartCount }}
    >
      {children}
    </CartContext.Provider>
  );
};
