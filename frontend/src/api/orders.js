import api from './axios';

// ─── Cashfree helper ───────────────────────────────────────────────────────────

/**
 * Initiate Cashfree checkout using the payment session ID.
 * 
 * @param {object} paymentParams - Cashfree payment parameters from backend
 * @param {string} paymentParams.payment_session_id - Payment session ID from Cashfree
 */
export function initiateCashfreeCheckout(paymentParams) {
    if (!paymentParams?.payment_session_id) {
        throw new Error('payment_session_id is required');
    }

    const { payment_session_id } = paymentParams;
    const env = import.meta.env.VITE_CASHFREE_ENV || 'sandbox';

    // Initialize Cashfree
    if (!window.Cashfree) {
        throw new Error('Cashfree SDK not loaded');
    }

    const cashfree = window.Cashfree({ mode: env });
    cashfree.checkout({
        paymentSessionId: payment_session_id,
        redirectTarget: '_self'
    });
}

// ─── Order creation ───────────────────────────────────────────────────────────

/** Create a single-book order (physical or ebook) */
export const createOrder = async (bookId, orderType, shippingData = {}) => {
    const response = await api.post('/api/orders/create-order/', {
        book_id: bookId,
        order_type: orderType,
        ...shippingData,
    });
    return response.data;
};

/** Create an ebook-specific purchase */
export const createEbookPurchase = async (bookId, customerData) => {
    const response = await api.post('/api/orders/ebook-purchase/', {
        book_id: bookId,
        ...customerData,
    });
    return response.data;
};

/** Create a cart checkout session */
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
 * @param {string} orderId - The Cashfree order ID
 */
export const verifyCashfreePayment = async (orderId) => {
    const response = await api.post('/api/orders/verify-cashfree-payment/', {
        order_id: orderId
    });
    return response.data;
};

// ─── Library & orders ───────────────────────────────────────────────────────────

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

/** Returns the full URL for the secure PDF endpoint */
export const getSecurePdfUrl = (bookId) => {
    const base = import.meta.env.VITE_API_URL || 'https://kavithedal-api.onrender.com';
    return `${base}/api/books/${bookId}/pdf/`;
};

// ─── Reading Progress ───────────────────────────────────────────────────────────

export const updateReadingProgress = async (bookId, progressData) => {
    const response = await api.post(`/api/books/${bookId}/reading-progress/update/`, progressData);
    return response.data;
};

export const getReadingProgress = async (bookId) => {
    const response = await api.get(`/api/books/${bookId}/reading-progress/`);
    return response.data;
};

export const checkEbookAccess = async (bookId) => {
    const response = await api.get(`/api/books/${bookId}/check-access/`);
    return response.data;
};