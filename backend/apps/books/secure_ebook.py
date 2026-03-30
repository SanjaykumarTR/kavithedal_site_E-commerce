"""
Secure ebook access utilities for Kavithedal Publications.
Implements Cloudinary signed URLs and secure PDF access control.
"""
import logging
import hashlib
import hmac
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('apps')


def get_cloudinary_config():
    """Get Cloudinary configuration from settings."""
    return {
        'cloud_name': getattr(settings, 'CLOUDINARY_CLOUD_NAME', ''),
        'api_key': getattr(settings, 'CLOUDINARY_API_KEY', ''),
        'api_secret': getattr(settings, 'CLOUDINARY_API_SECRET', ''),
    }


def is_cloudinary_configured():
    """Check if Cloudinary is properly configured."""
    config = get_cloudinary_config()
    return all(config.values())


def generate_cloudinary_signature(public_id, transformation='', duration=300):
    """
    Generate a Cloudinary signed URL for secure PDF access.
    
    Args:
        public_id: The Cloudinary public ID of the PDF file
        transformation: Optional transformation string
        duration: URL validity in seconds (default 5 minutes)
    
    Returns:
        dict with signed_url, expires_at, and signature components
    """
    config = get_cloudinary_config()
    
    if not all([config['cloud_name'], config['api_key'], config['api_secret']]):
        logger.error("Cloudinary not properly configured")
        return None
    
    # Calculate expiration time
    expires_at = int((timezone.now() + timedelta(seconds=duration)).timestamp())
    
    # For raw files, we can use the simpler approach with Cloudinary SDK
    try:
        import cloudinary
        from cloudinary.utils import cloudinary_url
        
        # Use Cloudinary's built-in signed URL generation
        url, options = cloudinary_url(
            public_id,
            resource_type='raw',
            sign_url=True,
            secure=True,
            sign=True,
            expires_at=expires_at
        )
        
        logger.info(f"Generated Cloudinary signed URL for {public_id}")
        
        return {
            'signed_url': url,
            'expires_at': expires_at,
            'signature': options.get('signature', ''),
            'public_id': public_id,
            'duration_seconds': duration,
        }
    except Exception as e:
        logger.warning(f"Cloudinary SDK signing failed: {e}, using fallback")
        
        # Fallback: Return simple unsigned URL for now
        # This will work if the file is set to 'authenticated' or 'public'
        base_url = f"https://res.cloudinary.com/{config['cloud_name']}/raw/upload"
        unsigned_url = f"{base_url}/{public_id}"
        
        return {
            'signed_url': unsigned_url,
            'expires_at': expires_at,
            'signature': 'fallback',
            'public_id': public_id,
            'duration_seconds': duration,
            'unsigned': True,
        }


def verify_cloudinary_signature(public_id, expires_at_str, signature):
    """
    Verify a Cloudinary signature (for webhook validation if needed).
    
    Args:
        public_id: The Cloudinary public ID
        expires_at_str: The expiration timestamp as string
        signature: The signature to verify
    
    Returns:
        bool indicating if signature is valid
    """
    config = get_cloudinary_config()
    
    if not all([config['cloud_name'], config['api_key'], config['api_secret']]):
        return False
    
    try:
        expires_at = int(expires_at_str)
        
        # Check if expired
        if timezone.now().timestamp() > expires_at:
            return False
        
        # Recalculate signature
        to_sign = f"{expires_at}/{public_id}"
        expected_signature = hmac.new(
            config['api_secret'].encode('utf-8'),
            to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except (ValueError, TypeError):
        return False


def get_pdf_url_from_cloudinary(public_id, use_signed=True, duration=300):
    """
    Get PDF URL from Cloudinary with optional signing.
    
    Args:
        public_id: The Cloudinary public ID of the PDF file
        use_signed: Whether to generate a signed URL
        duration: URL validity in seconds
    
    Returns:
        str: The PDF URL (signed or unsigned)
    """
    config = get_cloudinary_config()
    
    if not config['cloud_name']:
        logger.error("Cloudinary cloud name not configured")
        return None
    
    base_url = f"https://res.cloudinary.com/{config['cloud_name']}/raw/upload"
    
    if use_signed and config['api_secret']:
        result = generate_cloudinary_signature(public_id, duration=duration)
        return result['signed_url'] if result else None
    else:
        # Return unsigned URL (not recommended for production)
        return f"{base_url}/{public_id}"


def extract_public_id_from_cloudinary_url(url):
    """
    Extract the public ID from a Cloudinary URL.
    
    Args:
        url: Full Cloudinary URL
    
    Returns:
        str or None: The extracted public ID
    """
    if not url or 'res.cloudinary.com' not in url:
        return None
    
    try:
        # Try different URL formats
        # Format 1: https://res.cloudinary.com/{cloud}/raw/upload/{public_id}
        parts = url.split('/raw/upload/')
        if len(parts) > 1:
            public_id = parts[1].split('?')[0]  # Remove query params
            return public_id
        
        # Format 2: https://res.cloudinary.com/{cloud}/image/upload/{public_id}
        parts = url.split('/image/upload/')
        if len(parts) > 1:
            public_id = parts[1].split('?')[0]  # Remove query params
            return public_id
        
        # Format 3: Handle auto-upload format
        # For uploads without explicit folder, try to extract after version/folder
        import re
        match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\?|$)', url)
        if match:
            return match.group(1)
            
    except Exception as e:
        logger.error(f"Failed to extract public ID from URL: {e}")
    
    return None


def generate_access_token(user_id, book_id, purchase_id):
    """
    Generate a secure access token for ebook reading.
    
    Args:
        user_id: User's ID
        book_id: Book's ID
        purchase_id: Purchase record ID
    
    Returns:
        dict with token and expiration info
    """
    import secrets
    
    # Generate unique token
    raw_token = f"{user_id}:{book_id}:{purchase_id}:{secrets.token_urlsafe(32)}"
    
    # Create hash for storage (not reversible)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    expires_at = timezone.now() + timedelta(minutes=30)
    
    return {
        'token': raw_token,  # This would be sent to frontend
        'token_hash': token_hash,  # This would be stored for verification
        'expires_at': expires_at,
        'expires_in_minutes': 30,
    }


def validate_access_token(token, token_hash, expires_at):
    """
    Validate an access token.
    
    Args:
        token: The raw token from frontend
        token_hash: The stored hash
        expires_at: Token expiration datetime
    
    Returns:
        bool: Whether the token is valid
    """
    # Check expiration
    if timezone.now() > expires_at:
        return False
    
    # Verify hash matches
    expected_hash = hashlib.sha256(token.encode()).hexdigest()
    return hmac.compare_digest(token_hash, expected_hash)