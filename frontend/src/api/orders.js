import api from './axios';

// ─── PayU helper ─────────────────────────────────────────────────────────────

/**
 * Open PayU hosted checkout.
 * Creates an auto-submitting form with PayU parameters and redirects the user.
 *
 * @param {object} paymentParams - PayU payment parameters from backend
 * @param {string} paymentParams.payu_order_id - Unique PayU transaction ID
 * @param {string} paymentParams.amount - Amount to charge
 * @param {string} paymentParams.product_info - Product description
 * @param {string} paymentParams.firstname - Customer name
 * @param {string} paymentParams.email - Customer email
 * @param {string} paymentParams.phone - Customer phone
 * @param {string} paymentParams.surl - Success URL
 * @param {string} paymentParams.furl - Failure URL
 * @param {string} paymentParams.hash - SHA-512 hash for verification
 * @param {string} paymentParams.key - PayU merchant key
 */
export function initiatePayuCheckout(paymentParams) {
  console.log('=== PayU Checkout Debug ===');
  console.log('Payment params:', paymentParams);

  if (!paymentParams) {
    throw new Error('Payment parameters are required');
  }

  const {
    payu_order_id: txnid,
    amount,
    product_info: productinfo,
    firstname,
    email,
    phone,
    surl,
    furl,
    hash,
    key,
  } = paymentParams;

  if (!txnid || !amount || !productinfo || !firstname || !email || !hash || !key) {
    throw new Error('Missing required PayU parameters');
  }

  // Determine PayU environment
  const env = import.meta.env.VITE_PAYU_ENV || 'sandbox';
  const payuUrl = env === 'production'
    ? 'https://secure.payu.in/_payment'
    : 'https://test.payu.in/_payment';

  console.log('PayU environment:', env);
  console.log('PayU URL:', payuUrl);
  console.log('Transaction ID:', txnid);
  console.log('Amount:', amount);

  // Build form
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = payuUrl;
  form.style.display = 'none';

  // Required PayU fields
  const fields = [
    { name: 'key', value: key },
    { name: 'txnid', value: txnid },
    { name: 'amount', value: amount },
    { name: 'productinfo', value: productinfo },
    { name: 'firstname', value: firstname },
    { name: 'email', value: email },
    { name: 'phone', value: phone },
    { name: 'surl', value: surl },
    { name: 'furl', value: furl },
    { name: 'hash', value: hash },
  ];

  // Add hidden input fields
  fields.forEach(field => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = field.name;
    input.value = field.value;
    form.appendChild(input);
  });

  // Append form to body and submit
  document.body.appendChild(form);
  form.submit();
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
 * Verify a PayU payment by order_id.
 * Called from PurchaseSuccess.jsx after PayU redirects back.
 *
 * @param {string} payuOrderId - The PayU transaction ID (kv-eb-xxx / kv-ph-xxx / kv-ct-xxx)
 * @param {object} payuResponse - Full PayU POST response data (optional, if received from redirect)
 */
export const verifyPayuPayment = async (payuOrderId, payuResponse = null) => {
  // Optionally send PayU response for server-side verification
  const payload = { order_id: payuOrderId };
  if (payuResponse) {
    payload.payu_data = payuResponse;
  }

  const response = await api.post('/api/orders/verify-payu-payment/', payload);
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

/** Returns the full URL for the secure PDF endpoint */
export const getSecurePdfUrl = (bookId) => {
  const base = import.meta.env.VITE_API_URL || 'https://kavithedal-api.onrender.com';
  return `${base}/api/books/${bookId}/pdf/`;
};

// ─── Reading Progress ─────────────────────────────────────────────────────────

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
