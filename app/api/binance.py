import time
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, Optional

from app.utils import generate_binance_signature, make_binance_request, make_binance_c2c_request
from app.config import get_settings
from app.models.schemas import TopPriceResponse, AdType

router = APIRouter()

@router.get("/top-price", response_model=TopPriceResponse, summary="Get top USDT/TZS ads")
async def get_top_price(
    ad_type: Optional[AdType] = Query(None, description="Type of ad (BUY or SELL). If not provided, returns both.")
):
    """
    Fetches top prices for USDT/TZS ads from Binance C2C market.
    
    - If ad_type is specified, returns top price for that type only
    - If ad_type is not specified, returns top prices for both BUY and SELL
    
    Returns:
        TopPriceResponse: Object containing top prices and trader nicknames
    """
    settings = get_settings()
    
    # Define base parameters for Binance API request
    # Using correct format for C2C SAPI as per documentation
    base_params = {
        "fiat": "TZS",
        "asset": "USDT",
        "rows": 10,
        "page": 1,
        "timestamp": int(time.time() * 1000),
        "tradeType": ""  # Will be set in the loop
    }
    
    result = {}
    
    try:
        # If ad_type is specified, fetch only that type
        if ad_type:
            ad_types = [ad_type]
        else:
            # Otherwise fetch both BUY and SELL
            ad_types = [AdType.BUY, AdType.SELL]
            
        for type_value in ad_types:
            # Create parameters for specific ad type
            params = base_params.copy()
            params["tradeType"] = type_value.value
            
            # Make request to Binance API using our C2C SAPI method
            response = make_binance_c2c_request(
                endpoint="/sapi/v1/c2c/ads/search",
                params=params,
                api_key=settings.api_key,
                api_secret=settings.api_secret,
                method="POST"
            )
            
            # Process response - format according to C2C SAPI documentation
            if response and "data" in response and response["data"]:
                # Sort ads by price (ascending for BUY, descending for SELL)
                ads = response["data"]
                if type_value == AdType.BUY:
                    # For BUY ads, buyers want lowest price
                    sorted_ads = sorted(ads, key=lambda x: float(x.get("adv", {}).get("price", 0)))
                else:
                    # For SELL ads, sellers want highest price
                    sorted_ads = sorted(ads, key=lambda x: float(x.get("adv", {}).get("price", 0)), reverse=True)
                
                if sorted_ads:
                    top_ad = sorted_ads[0]["adv"]
                    result[type_value.value.lower()] = {
                        "price": float(top_ad.get("price", 0)),
                        "nickname": top_ad.get("advertiser", {}).get("nickName", "Unknown")
                    }
            else:
                result[type_value.value.lower()] = None
                
        return TopPriceResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching top prices from Binance: {str(e)}"
        )
