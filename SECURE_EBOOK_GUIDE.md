# Secure Ebook System - Implementation Guide

## Overview

This document describes the secure ebook reading system implemented for Kavithedal Publications. The system ensures that only authenticated users who have purchased ebooks can access them, with time-limited URLs and anti-piracy measures.

---

## Architecture

### Secure Flow

```
User → Login → Buy Ebook → Payment Success → Backend verifies purchase
    ↓
Store in UserLibrary + EbookPurchase → Generate access token
    ↓
User requests /reader/:bookId → Backend validates purchase
    ↓
Generate signed Cloudinary URL (5-minute expiration)
    ↓
Frontend renders PDF with react-pdf + watermark
    ↓
Reading progress tracked automatically
```

---

## Backend Components

### 1. Models (`backend/apps/orders/models.py`)

**EbookPurchase Model** - Enhanced with:
- `access_token`: Unique token for secure PDF access
- `access_token_created`: When the token was generated
- `access_token_expires`: Token expiration time (30 minutes)
- `order_id`: Cashfree order ID for tracking
- `cashfree_order_id` / `cashfree_payment_id`: Payment gateway fields
- `current_page`: User's current reading position
- `reading_progress`: JSON field for storing reading metadata

### 2. Secure PDF API (`backend/apps/books/views.py`)

**SecureFileView** (`GET /api/books/<uuid:book_id>/pdf/`):
- Validates user authentication
- Checks UserLibrary OR EbookPurchase (with completed payment)
- Allows admin preview access
- Generates Cloudinary signed URL
- Returns temporary URL with 5-minute expiration

**check_pdf_access** (`GET /api/books/<uuid:book_id>/check-access/`):
- Returns whether user has access
- Includes reading progress data

**update_reading_progress** (`POST /api/books/<uuid:book_id>/reading-progress/update/`):
- Saves current page and metadata
- Updates progress_percent in reading_progress

**get_reading_progress** (`GET /api/books/<uuid:book_id>/reading-progress/`):
- Returns saved reading position

### 3. Cloudinary Utilities (`backend/apps/books/secure_ebook.py`)

- `generate_cloudinary_signature()`: Creates time-limited signed URLs
- `get_pdf_url_from_cloudinary()`: Returns signed URL for PDF
- `extract_public_id_from_cloudinary_url()`: Extracts Cloudinary public ID
- `generate_access_token()`: Creates secure access tokens
- `validate_access_token()`: Verifies token validity

### 4. Storage Configuration (`backend/apps/books/cloudinary_storage.py`)

- `RawCloudinaryStorage`: Uploads PDFs as 'authenticated' type (NOT public)
- `PrivatePDFStorage`: Alternative for maximum security with 'private' type

---

## Frontend Components

### 1. Reader Component (`frontend/src/pages/Reader.jsx`)

**Features**:
- react-pdf for in-app PDF rendering (not external viewer)
- Page navigation with keyboard support
- Zoom controls (50% - 250%)
- Dark/Light mode toggle
- Fullscreen mode
- Auto-hiding controls

**Security Features**:
- Right-click disabled
- Ctrl+P (Print), Ctrl+S (Save), Ctrl+U (View Source) disabled
- Print Screen disabled
- Select All disabled (except in input fields)
- Iframe embedding detection and prevention

**Watermark**:
- User email displayed on every page
- Semi-transparent overlay (opacity: 0.15)
- Rotated at -45 degrees across the page

**Reading Progress**:
- Auto-saves position every 2 seconds (debounced)
- Resumes from last position on next access
- Tracks scale preference

### 2. API Functions (`frontend/src/api/orders.js`)

- `updateReadingProgress(bookId, data)`: Save progress
- `getReadingProgress(bookId)`: Retrieve saved position
- `checkEbookAccess(bookId)`: Verify access + get metadata

---

## Cloudinary Configuration

### Required Environment Variables

```env
# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Optional: Set PDF upload type
# 'authenticated' = requires signed URLs (recommended)
# 'private' = requires Cloudinary authentication (maximum security)
CLOUDINARY_PDF_UPLOAD_TYPE=authenticated
```

### Cloudinary Dashboard Settings

1. **Upload Settings**:
   - Go to Settings → Upload
   - Under "Upload presets", create a new preset for PDFs:
     - Signing Mode: "Unsigned" (for admin uploads) OR "Signed" (for API-only uploads)
     - Resource Type: "Raw"
     - Folder: `books/pdfs`

2. **Security Settings**:
   - Go to Settings → Security
   - Ensure "Restricted image types" are blocked
   - Enable "Delivery from CDN only" for production

3. **For PDFs specifically**:
   - PDFs should be set to 'authenticated' access type
   - This means direct URLs will NOT work without signed parameters

### Signed URL Generation

Cloudinary signed URLs include:
- `expires_at`: Unix timestamp when URL expires
- `signature`: HMAC-SHA256 signature using API secret

Example signed URL format:
```
https://res.cloudinary.com/{cloud}/raw/upload/fl_signerate/{public_id}?--expires-at={timestamp}&--signature={sig}
```

---

## Anti-Piracy Measures

### Backend Protections

1. **Authentication Required**: All PDF endpoints require valid JWT token
2. **Purchase Verification**: User must have valid purchase record
3. **Time-Limited URLs**: PDF URLs expire after 5 minutes
4. **Access Token System**: Each request generates a new token
5. **Admin Preview**: Admins can preview but with limited access

### Frontend Protections

1. **No Download Button**: PDF cannot be downloaded via UI
2. **Watermark Overlay**: User email on every page
3. **Disabled Shortcuts**: Print, Save, View Source all blocked
4. **Content Selection Disabled**: Text cannot be selected/copied
5. **Iframe Detection**: Prevents embedding on other sites
6. **Print Media Query**: `display: none` for print styles

### Cloudinary Protections

1. **Authenticated Files**: PDFs are NOT public
2. **Signed URLs Required**: Every access needs valid signature
3. **CORS Configuration**: Restrict to your domain only
4. **CDN Only Delivery**: Prevents direct server access

---

## Deployment Checklist

### Backend

- [ ] Run migrations: `python manage.py migrate`
- [ ] Set environment variables in Render dashboard:
  - `CLOUDINARY_CLOUD_NAME`
  - `CLOUDINARY_API_KEY`
  - `CLOUDINARY_API_SECRET`
  - `CLOUDINARY_PDF_UPLOAD_TYPE=authenticated`
- [ ] Verify Cloudinary credentials are working
- [ ] Test signed URL generation

### Frontend

- [ ] Install dependencies: `npm install`
- [ ] Add react-pdf and pdfjs-dist packages
- [ ] Update vite.config.js with PDF worker configuration
- [ ] Test reader on mobile and desktop
- [ ] Verify watermark displays correctly

### Cloudinary

- [ ] Upload existing PDFs with 'authenticated' type
- [ ] Verify direct URLs return 403 (not public)
- [ ] Test signed URL generation and expiration
- [ ] Check CORS settings for your domain

---

## Testing

### Test Cases

1. **Unauthenticated Access**: ❌ Should return 401/403
2. **Authenticated but No Purchase**: ❌ Should return 403
3. **Valid Purchase**: ✅ Should return signed URL
4. **Expired URL**: ❌ Should return 403/404
5. **Admin Preview**: ✅ Should work for admins
6. **Reading Progress**: ✅ Should save and restore

### Manual Testing

1. Create test user
2. Purchase an ebook
3. Verify in UserLibrary/EbookPurchase
4. Navigate to /reader/:bookId
5. Check browser console for errors
6. Verify watermark appears
7. Test page navigation
8. Close and reopen - should resume position

---

## Troubleshooting

### "PDF file is not accessible" error

1. Check Cloudinary credentials are set
2. Verify PDF was uploaded as 'raw' type
3. Ensure file exists in Cloudinary dashboard
4. Check the public_id extraction is working

### Watermark not showing

1. Ensure `.watermark-overlay` CSS has `pointer-events: none`
2. Check z-index is above PDF content
3. Verify user email is being passed correctly

### PDF not loading in reader

1. Check browser console for CORS errors
2. Verify signed URL is being generated
3. Test the URL directly in browser
4. Check Cloudinary upload type is 'raw'

### Reading progress not saving

1. Verify `/api/books/:id/reading-progress/update/` endpoint works
2. Check that EbookPurchase record exists with completed status
3. Ensure user is authenticated

---

## Future Enhancements

### Optional Features (Not Implemented)

1. **Bookmarks**: Save and retrieve bookmark positions
2. **Notes/Highlights**: Allow users to highlight text and add notes
3. **Search**: Full-text search within PDFs
4. **Offline Support**: Service worker for offline reading
5. **Download Limit**: Limit downloads per purchase
6. **Device Tracking**: Track which devices access the content
7. **Watermark Customization**: Dynamic watermark position/rotation

### Production Hardening

1. **Rate Limiting**: Limit PDF access requests per user
2. **IP Logging**: Log IP addresses for access auditing
3. **Watermark Timestamp**: Add access timestamp to watermark
4. **Screenshot Detection**: Detect and log screenshot attempts
5. **DRM Integration**: Consider third-party DRM solutions

---

## Summary

This secure ebook system provides:

✅ **Authentication**: Only logged-in users can access
✅ **Authorization**: Only purchasers can read
✅ **Time-Limited URLs**: 5-minute expiration prevents sharing
✅ **In-App Reading**: PDF rendered inside app, not external
✅ **Anti-Piracy**: Watermark, disabled shortcuts, no download
✅ **Reading Progress**: Resume from last position
✅ **Cloudinary Security**: Authenticated files, signed URLs

The system is production-ready and follows security best practices for digital content delivery.