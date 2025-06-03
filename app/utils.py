import hmac
import hashlib
import time
import urllib.parse
import logging
import json
from typing import Dict, Any, Optional

import requests
from fastapi import HTTPException

from app.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

def generate_binance_signature(query_string: str, secret_key: str) -> str:
    """
    Generate HMAC SHA256 signature for Binance API authentication
    
    Args:
        query_string: URL encoded query parameters
        secret_key: Binance API secret key
        
    Returns:
        str: HMAC SHA256 signature as hex digest
    """
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def make_binance_request(
    endpoint: str, 
    params: Dict[str, Any], 
    api_key: str,
    api_secret: str,
    method: str = "GET"
) -> Dict[str, Any]:
    """
    Make authenticated request to Binance API
    
    Args:
        endpoint: API endpoint path
        params: Query parameters
        api_key: Binance API key
        api_secret: Binance API secret
        method: HTTP method (GET or POST)
        
    Returns:
        Dict: Response from Binance API
        
    Raises:
        HTTPException: On API request failure
    """
    settings = get_settings()
    
    # Ensure timestamp is in the parameters
    if 'timestamp' not in params:
        params['timestamp'] = int(time.time() * 1000)
    
    # Convert parameters to query string
    query_string = urllib.parse.urlencode(params)
    
    # Generate signature
    signature = generate_binance_signature(query_string, api_secret)
    
    # Add signature to parameters
    query_string = f"{query_string}&signature={signature}"
    
    # Construct full URL
    url = f"{settings.binance_api_url}{endpoint}"
    
    # Prepare headers based on the SAPI documentation
    headers = {
        "X-MBX-APIKEY": api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "clientType": "web" # Required per SAPI documentation
    }
    
    logger.info(f"Making direct request to {endpoint}")
    
    try:
        if method.upper() == "GET":
            url = f"{url}?{query_string}"
            response = requests.get(url, headers=headers)
        else:  # POST, PUT, etc.
            response = requests.post(
                url, 
                headers=headers, 
                data=query_string
            )
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Handle and log the API error
        error_detail = f"Binance API error: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_body = e.response.json()
                if 'msg' in error_body:
                    error_detail = f"Binance API error: {error_body.get('msg')}"
                elif 'message' in error_body:
                    error_detail = f"Binance API error: {error_body.get('message')}"
            except ValueError:
                if hasattr(e.response, 'text'):
                    error_detail = f"Binance API error: {e.response.text}"
                
        logger.error(f"API request failed: {error_detail}")
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )

def make_binance_c2c_request(
    endpoint: str,
    params: Dict[str, Any],
    api_key: str,
    api_secret: str,
    method: str = "POST"
) -> Dict[str, Any]:
    """
    Make authenticated request to Binance C2C SAPI
    
    Args:
        endpoint: API endpoint path (should start with /sapi/v1/c2c/)
        params: Query parameters
        api_key: Binance API key
        api_secret: Binance API secret
        method: HTTP method (GET or POST, most C2C SAPI endpoints use POST)
        
    Returns:
        Dict: Response from Binance API
        
    Raises:
        HTTPException: On API request failure
    """
    settings = get_settings()
    
    # Ensure timestamp is in the parameters
    if 'timestamp' not in params:
        params['timestamp'] = int(time.time() * 1000)
    
    # For C2C SAPI POST requests with JSON body
    if method.upper() == "POST" and endpoint.startswith("/sapi/v1/c2c/"):
        # Convert parameters to query string for signature
        params_for_signature = params.copy()
        query_string = urllib.parse.urlencode(params_for_signature)
        
        # Generate signature
        signature = generate_binance_signature(query_string, api_secret)
        
        # Construct full URL with signature
        url = f"{settings.binance_api_url}{endpoint}?{query_string}&signature={signature}"
        
        # Prepare headers according to SAPI documentation
        headers = {
            "X-MBX-APIKEY": api_key,
            "Content-Type": "application/json",
            "clientType": "web"
        }
        
        logger.info(f"Making direct C2C SAPI request to {endpoint}")
        
        try:
            # For C2C SAPI, sometimes we need to include the params in the URL and sometimes in the body
            # The approach depends on the specific endpoint requirements
            if "/ads/search" in endpoint or "/ads/getReferencePrice" in endpoint:
                # These endpoints need the params in the body as JSON
                # Remove timestamp and signature from body
                body_params = {k: v for k, v in params.items() if k not in ['timestamp']}
                response = requests.post(
                    url,
                    headers=headers,
                    json=body_params
                )
            else:
                # Default approach - all params in the URL, empty body
                response = requests.post(
                    url,
                    headers=headers
                )
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Handle and log the API error
            error_detail = f"Binance API error: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    if 'msg' in error_body:
                        error_detail = f"Binance API error: {error_body.get('msg')}"
                        # Check for geographical restriction
                        if "restricted location" in error_detail.lower():
                            error_detail = "Binance API access is restricted from your current location. Please ensure you're accessing from a supported region or configure proper network routing."
                    elif 'message' in error_body:
                        error_detail = f"Binance API error: {error_body.get('message')}"
                except ValueError:
                    if hasattr(e.response, 'text'):
                        error_detail = f"Binance API error: {e.response.text}"
                        if "restricted location" in error_detail.lower():
                            error_detail = "Binance API access is restricted from your current location. Please ensure you're accessing from a supported region or configure proper network routing."
                    
            logger.error(f"API request failed: {error_detail}")
            raise HTTPException(
                status_code=500,
                detail=error_detail
            )
    else:
        # For non-C2C endpoints or GET requests, use the standard method
        return make_binance_request(endpoint, params, api_key, api_secret, method)
