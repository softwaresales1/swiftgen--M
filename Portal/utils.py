import urllib.parse
import unicodedata
import re

def safe_cookie_value(value):
    """
    Convert a value to a safe cookie value that can be encoded in ASCII.
    This prevents the Unicode encoding error.
    """
    if value is None:
        return ''
    
    # Convert to string
    str_value = str(value)
    
    # URL encode the value to handle Unicode characters
    encoded_value = urllib.parse.quote(str_value, safe='')
    
    return encoded_value

def get_cookie_value(request, key, default=''):
    """
    Safely retrieve and decode a cookie value.
    """
    encoded_value = request.COOKIES.get(key, default)
    if encoded_value:
        try:
            return urllib.parse.unquote(encoded_value)
        except:
            return default
    return default

def clean_filename(filename):
    """
    Clean filename to remove Unicode characters that might cause issues.
    """
    # Normalize Unicode characters
    filename = unicodedata.normalize('NFKD', filename)
    
    # Remove non-ASCII characters
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Remove special characters except dots, hyphens, and underscores
    filename = re.sub(r'[^\w\s.-]', '', filename).strip()
    
    # Replace spaces with hyphens
    filename = re.sub(r'[-\s]+', '-', filename)
    
    return filename

def safe_string_for_database(text):
    """
    Clean text for safe database storage by normalizing Unicode.
    """
    if not text:
        return ''
    
    # Normalize Unicode to NFC form (canonical composition)
    normalized = unicodedata.normalize('NFC', str(text))
    
    # Replace problematic Unicode quotes with standard ones
    normalized = normalized.replace('\u2018', "'")  # Left single quote
    normalized = normalized.replace('\u2019', "'")  # Right single quote
    normalized = normalized.replace('\u201c', '"')  # Left double quote
    normalized = normalized.replace('\u201d', '"')  # Right double quote
    normalized = normalized.replace('\u2013', '-')  # En dash
    normalized = normalized.replace('\u2014', '-')  # Em dash
    
    return normalized