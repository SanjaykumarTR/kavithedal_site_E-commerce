import api from './axios';

// ─── Cashfree helper ──────────────────────────────────────────────────────────

/**
 * Open Cashfree checkout.
 * Requires the Cashfree JS SDK script loaded in index.html.
 * On success/failure Cashfree redirects to the return_url set by the backend.
 *
 * @param {string} paymentSessionId  - returned by the backend create-order endpoints
 */
export function initiateCashfreeCheckout(paymentSessionId) {
  console.log('=== Cashfree Checkout Debug ===');
  console.log('paymentSessionId:', paymentSessionId);
  console.log('paymentSessionId type:', typeof paymentSessionId);
  console.log('paymentSessionId length:', paymentSessionId ? paymentSessionId.length : 0);
  console.log('window.Cashfree exists:', !!window.Cashfree);
  
  if (!paymentSessionId) {
    throw new Error('paymentSessionId is empty or undefined');
  }
  
  if (!window.Cashfree) {
    throw new Error(
      'Cashfree SDK is not loaded yet. Please wait a moment and try again.'
    );
  }
  
  const mode = import.meta.env.VITE_CASHFREE_ENV || 'sandbox';
  console.log('Cashfree mode:', mode);
  
  const cashfree = window.Cashfree({ mode });
  console.log('Calling cashfree.checkout with paymentSessionId:', paymentSessionId);
  
  cashfree.checkout({
    paymentSessionId,
    redirectTarget: '_self',   // redirect in the same tab
  });
}

// ─── Order creation ───────────────────────────────────────────────────────────

/** Create a single-book order (physical or ebook) via CreateOrderView. */
export const createOrder = async (bookId, orderType, shippingData = {}) => {
  const response = await api.post('/api/orders/create-order/', {
    book_id: bookId,
    order_type: orderType,
    ...shippingData,
  });
  return response.data;
};

/** Create an ebook-specific purchase (EbookPurchaseView). */
export const createEbookPurchase = async (bookId, customerData) => {
  const response = await api.post('/api/orders/ebook-purchase/', {
    book_id: bookId,
    ...customerData,
  });
  return response.data;
};

/** Create a cart checkout session (CartCheckoutView). */
export const createCartCheckout = async (items, totalAmount, phone = '') => {
  const response = await api.post('/api/orders/cart-checkout/', {
    items,
    total_amount: totalAmount,
    phone,
  });
  return response.data;
};

// ─── Payment verification ─────────────────────────────────────────────────────

/**
 * Verify a Cashfree payment by order_id.
 * Called from PurchaseSuccess.jsx after Cashfree redirects back.
 *
 * @param {string} cashfreeOrderId  - the kv-eb-xxx / kv-ph-xxx / kv-ct-xxx ID
 */
export const verifyCashfreePayment = async (cashfreeOrderId) => {
  const response = await api.get('/api/orders/verify-cashfree-payment/', {
    params: { order_id: cashfreeOrderId },
  });
  return response.data;
};

// ─── Library & orders ─────────────────────────────────────────────────────────

export const getUserLibrary = async () => {
  const response = await api.get('/api/orders/library/');
  return response.data;
};

export const checkBookAccess = async (bookId) => {
  const response = await api.get(`/api/books/${bookId}/check-access/`);
  return response.data;
};

export const getUserOrders = async () => {
  const response = await api.get('/api/orders/orders/');
  return response.data;
};

/** Returns the full URL for the secure PDF endpoint (used by Reader.jsx). */
export const getSecurePdfUrl = (bookId) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  return `${base}/api/books/${bookId}/pdf/`;
};

// ─── Reading Progress ─────────────────────────────────────────────────────────

/**
 * Update reading progress for an ebook.
 * @param {string} bookId - The book ID
 * @param {object} progressData - { page, total_pages, metadata }
 */
export const updateReadingProgress = async (bookId, progressData) => {
  const response = await api.post(`/api/books/${bookId}/reading-progress/update/`, progressData);
  return response.data;
};

/**
 * Get reading progress for an ebook.
 * @param {string} bookId - The book ID
 * @returns {object} - { current_page, reading_progress, purchase_id }
 */
export const getReadingProgress = async (bookId) => {
  const response = await api.get(`/api/books/${bookId}/reading-progress/`);
  return response.data;
};

/**
 * Check ebook access and get reading progress info.
 * @param {string} bookId - The book ID
 * @returns {object} - { has_access, has_pdf, current_page, reading_progress }
 */
export const checkEbookAccess = async (bookId) => {
  const response = await api.get(`/api/books/${bookId}/check-access/`);
  return response.data;
};
