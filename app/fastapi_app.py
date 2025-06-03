from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import time

from app.utils import make_binance_request, make_binance_c2c_request
from app.config import get_settings
from app.price_updater import start_price_updater, stop_price_updater, price_updater
from app.ml_price_analyzer import MLPriceAnalyzer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fastapi_app")

# Create FastAPI app
app = FastAPI(
    title="Binance C2C API",
    description="FastAPI application to interact with Binance C2C market",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure templates
templates = Jinja2Templates(directory="templates")

# Enum for ad types
class AdType:
    BUY = "BUY"
    SELL = "SELL"

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home(request: Request):
    """
    Renders the main dashboard using Jinja2 templates
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/top-price")
async def get_top_price(ad_type: Optional[str] = None):
    """
    Fetches top prices for USDT/TZS ads from Binance C2C market.
    
    Query Parameters:
        ad_type: Type of ad (BUY or SELL). If not provided, returns both.
    
    Returns:
        JSON Object containing top prices and trader nicknames
    """
    settings = get_settings()
    
    # Define base parameters for Binance API request per C2C SAPI documentation
    base_params = {
        "fiat": "TZS",
        "asset": "USDT",
        "rows": 10,
        "page": 1,
        "timestamp": int(time.time() * 1000),
        "tradeType": "",
        "payTypes": [],  # Payment methods (optional)
        "publisherType": None,  # Merchant or individual
        "transAmount": ""  # Transaction amount (optional)
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
            params["tradeType"] = type_value
            
            # Make request to Binance API using C2C SAPI client
            response = make_binance_c2c_request(
                endpoint="/sapi/v1/c2c/ads/search",
                params=params,
                api_key=settings.api_key,
                api_secret=settings.api_secret,
                method="POST"
            )
            
            # Process response
            if "data" in response and response["data"]:
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
                    result[type_value.lower()] = {
                        "price": float(top_ad.get("price", 0)),
                        "nickname": top_ad.get("advertiser", {}).get("nickName", "Unknown")
                    }
            else:
                result[type_value.lower()] = None
                
        return result
        
    except Exception as e:
        logger.error(f"Error fetching top prices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching top prices from Binance: {str(e)}")

@app.post("/api/release-order")
async def release_order(data: Dict[str, Any]):
    """
    Releases crypto to the buyer after confirming payment received
    
    Request Body:
        order_number: The C2C order number to release
        
    Returns:
        JSON Object containing the result of the release operation
    """
    settings = get_settings()
    
    try:
        # Extract required fields from request
        order_number = data.get('order_number')
        
        # Validate required fields
        if not order_number:
            raise HTTPException(status_code=400, detail="Missing required field: order_number is required")
        
        # Build parameters for Binance API
        params = {
            "orderNumber": str(order_number),
            "timestamp": int(time.time() * 1000)
        }
            
        # Make POST request to Binance API to release crypto using C2C SAPI
        response = make_binance_c2c_request(
            endpoint="/sapi/v1/c2c/orderMatch/releaseCoin",
            params=params,
            api_key=settings.api_key,
            api_secret=settings.api_secret,
            method="POST"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error releasing order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error releasing order: {str(e)}")

@app.post("/api/post-ad")
async def post_ad(data: Dict[str, Any]):
    """
    Creates a new ad on Binance C2C market
    
    Request Body:
        price: The price for the ad
        quantity: The amount of crypto to sell/buy
        trade_type: The type of ad (BUY or SELL)
        asset: The crypto asset (default: USDT)
        fiat: The fiat currency (default: TZS)
        min_limit: Minimum trade limit
        max_limit: Maximum trade limit
        pay_types: Payment methods (M-pesa, Tigo Pesa)
        
    Returns:
        JSON Object containing the result of the ad posting
    """
    settings = get_settings()
    
    try:
        # Extract required fields from request
        price = data.get('price')
        quantity = data.get('quantity')
        trade_type = data.get('trade_type')
        
        # Validate required fields
        if not all([price, quantity, trade_type]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: price, quantity, and trade_type are required"
            )
            
        # Extract optional fields with defaults
        asset = data.get('asset', 'USDT')
        fiat = data.get('fiat', 'TZS')
        min_limit = data.get('min_limit')
        max_limit = data.get('max_limit')
        pay_types = data.get('pay_types', ['M-pesa', 'Tigo Pesa'])
        
        # Validate pay_types
        valid_pay_types = ['M-pesa', 'Tigo Pesa']
        for pay_type in pay_types:
            if pay_type not in valid_pay_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid pay_type: {pay_type}. Valid options are: {', '.join(valid_pay_types)}"
                )
                
        # Build parameters for Binance API
        params = {
            "asset": asset,
            "fiat": fiat,
            "tradeType": trade_type,
            "price": str(price),
            "quantity": str(quantity),
            "payTypes": ','.join(pay_types),
            "timestamp": int(time.time() * 1000)
        }
        
        # Add optional parameters if provided
        if min_limit:
            params["minSingleTransAmount"] = str(min_limit)
        if max_limit:
            params["maxSingleTransAmount"] = str(max_limit)
            
        # Make POST request to Binance API
        response = make_binance_request(
            endpoint="/sapi/v1/c2c/ads/post",
            params=params,
            api_key=settings.api_key,
            api_secret=settings.api_secret,
            method="POST"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error posting ad: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=f"Error posting ad to Binance: {str(e)}")

@app.get("/api/leaderboard")
async def get_leaderboard(
    sort_by: str = "volume",
    asset: str = "USDT",
    fiat: str = "TZS",
    trade_type: Optional[str] = None,
    days: int = 30
):
    """
    Fetches the top 30 traders on Binance C2C market by volume or order count
    
    Query Parameters:
        sort_by: Field to sort by ('volume' or 'orders'). Default is 'volume'.
        asset: Crypto asset (default: USDT)
        fiat: Fiat currency (default: TZS)
        trade_type: Type of trade (BUY or SELL). If not provided, returns both.
        days: Number of days to look back (default: 30)
    
    Returns:
        JSON Object containing top traders
    """
    settings = get_settings()
    
    sort_by = sort_by.lower()
    if sort_by not in ['volume', 'orders']:
        raise HTTPException(
            status_code=400, 
            detail="Invalid sort_by parameter. Valid options are 'volume' or 'orders'."
        )
    
    try:
        # Create params for the Binance API request
        params = {
            "tradeType": trade_type.upper() if trade_type else None,
            "asset": asset,
            "fiat": fiat,
            "startTimestamp": int((time.time() - days * 86400) * 1000),  # days ago
            "endTimestamp": int(time.time() * 1000),  # now
            "timestamp": int(time.time() * 1000)
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        # Make request to Binance API to get all orders in the period
        response = make_binance_request(
            endpoint="/sapi/v1/c2c/orderMatch/listOrders",
            params=params,
            api_key=settings.api_key,
            api_secret=settings.api_secret
        )
        
        # Process the order data to create the leaderboard
        if "data" in response:
            orders = response.get("data", [])
            
            # Group by trader and aggregate volume and count
            trader_stats = {}
            
            for order in orders:
                # Extract trader info
                advertiser_name = order.get("advertiserNickname", "Unknown")
                
                # Calculate volume for this order
                try:
                    volume = float(order.get("totalPrice", 0))
                    
                    # Initialize trader entry if not exists
                    if advertiser_name not in trader_stats:
                        trader_stats[advertiser_name] = {
                            "nickname": advertiser_name,
                            "volume": 0.0,
                            "orders": 0,
                            "assets": set()
                        }
                    
                    # Update trader stats
                    trader_stats[advertiser_name]["volume"] += volume
                    trader_stats[advertiser_name]["orders"] += 1
                    trader_stats[advertiser_name]["assets"].add(order.get("asset", "Unknown"))
                except (ValueError, TypeError):
                    # Skip orders with invalid volume
                    continue
            
            # Convert stats to list and sort
            leaderboard = list(trader_stats.values())
            
            # Convert set to list for JSON serialization
            for trader in leaderboard:
                trader["assets"] = list(trader["assets"])
            
            # Sort by selected criteria
            if sort_by == 'volume':
                leaderboard.sort(key=lambda x: x["volume"], reverse=True)
            else:  # sort by order count
                leaderboard.sort(key=lambda x: x["orders"], reverse=True)
            
            # Take top 30
            top_traders = leaderboard[:30]
            
            return {
                "sort_by": sort_by,
                "days": days,
                "count": len(top_traders),
                "traders": top_traders
            }
        else:
            raise HTTPException(status_code=500, detail="No order data returned from Binance")
            
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=f"Error fetching leaderboard: {str(e)}")

@app.get("/api/price-updater/status")
async def get_updater_status():
    """
    Get the current status of the price updater
    
    Returns:
        JSON object with status information
    """
    status = "running" if price_updater and price_updater.running else "stopped"
    interval = price_updater.interval if price_updater else 30
    
    return {
        "status": status,
        "interval": interval,
        "updater_active": price_updater is not None
    }

@app.post("/api/price-updater/start")
async def start_updater(data: Dict[str, Any]):
    """
    Start the price updater
    
    Returns:
        JSON object with result
    """
    try:
        # Get interval from request if provided
        interval = data.get('interval', 30)
        
        if not isinstance(interval, int) or interval < 5:
            raise HTTPException(
                status_code=400,
                detail="Interval must be an integer of at least 5 seconds"
            )
            
        start_price_updater(interval=interval)
        
        return {
            "success": True,
            "message": f"Price updater started with interval {interval} seconds"
        }
        
    except Exception as e:
        logger.error(f"Error starting price updater: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=f"Error starting price updater: {str(e)}")

@app.post("/api/price-updater/stop")
async def stop_updater():
    """
    Stop the price updater
    
    Returns:
        JSON object with result
    """
    try:
        stop_price_updater()
        
        return {
            "success": True,
            "message": "Price updater stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping price updater: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping price updater: {str(e)}")

@app.post("/api/initialize")
async def api_initialize():
    """
    Initialize the application
    
    Returns:
        JSON object with result
    """
    try:
        # Start the price updater if API credentials are set
        settings = get_settings()
        if settings.api_key and settings.api_secret:
            logger.info("API credentials found, starting price updater")
            try:
                start_price_updater()
            except Exception as e:
                logger.error(f"Failed to start price updater: {str(e)}")
        else:
            logger.warning("API credentials not found, price updater will not start automatically")
            
        return {
            "success": True,
            "message": "Application initialized"
        }
    except Exception as e:
        logger.error(f"Error initializing application: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error initializing application: {str(e)}")

# Initialize app on startup
@app.on_event("startup")
async def startup_event():
    try:
        await api_initialize()
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

# Endpoints for ad filtering and blacklisting

@app.post("/api/filter/set-limits")
async def set_ad_filters(data: Dict[str, Any]):
    """
    Set the ad filtering options for the price updater
    
    Request Body:
        min_limit: Minimum transaction limit
        max_limit: Maximum transaction limit
        min_available: Minimum available amount
        min_completion_rate: Minimum completion rate percentage
        min_order_count: Minimum order count
        
    Returns:
        JSON Object with result of the operation
    """
    try:
        # Get analyzer instance from price updater
        if price_updater is None:
            return {"success": False, "message": "Price updater not initialized"}
            
        analyzer = price_updater.ml_analyzer
        
        # Update filters
        analyzer.set_limit_filters(
            min_limit=data.get("min_limit"),
            max_limit=data.get("max_limit"),
            min_available=data.get("min_available"),
            min_completion_rate=data.get("min_completion_rate"),
            min_order_count=data.get("min_order_count")
        )
        
        return {
            "success": True, 
            "message": "Ad filters updated successfully",
            "filters": {
                "min_limit": analyzer.min_limit_filter,
                "max_limit": analyzer.max_limit_filter,
                "min_available": analyzer.min_available_filter,
                "min_completion_rate": analyzer.min_completion_rate,
                "min_order_count": analyzer.min_order_count
            }
        }
    except Exception as e:
        logger.error(f"Error setting ad filters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/api/filter/get-limits")
async def get_ad_filters():
    """
    Get the current ad filtering options
    
    Returns:
        JSON Object with current filter settings
    """
    try:
        # Get analyzer instance from price updater
        if price_updater is None:
            return {"success": False, "message": "Price updater not initialized"}
            
        analyzer = price_updater.ml_analyzer
        
        return {
            "success": True,
            "filters": {
                "min_limit": analyzer.min_limit_filter,
                "max_limit": analyzer.max_limit_filter,
                "min_available": analyzer.min_available_filter,
                "min_completion_rate": analyzer.min_completion_rate,
                "min_order_count": analyzer.min_order_count
            }
        }
    except Exception as e:
        logger.error(f"Error getting ad filters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/api/blacklist/ban-advertiser")
async def ban_advertiser(data: Dict[str, Any]):
    """
    Add an advertiser to the restricted list
    
    Request Body:
        advertiser_id: ID of the advertiser to ban
        
    Returns:
        JSON Object with result of the operation
    """
    try:
        # Get analyzer instance from price updater
        if price_updater is None:
            return {"success": False, "message": "Price updater not initialized"}
            
        advertiser_id = data.get("advertiser_id")
        if not advertiser_id:
            return {"success": False, "message": "Advertiser ID is required"}
            
        analyzer = price_updater.ml_analyzer
        analyzer.flag_restricted_advertisers([advertiser_id])
        
        return {
            "success": True,
            "message": f"Advertiser {advertiser_id} added to restricted list",
            "restricted_count": len(analyzer.restricted_advertisers)
        }
    except Exception as e:
        logger.error(f"Error banning advertiser: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/api/blacklist/ban-ad")
async def ban_ad(data: Dict[str, Any]):
    """
    Add an ad to the blacklist
    
    Request Body:
        ad_id: ID of the ad to blacklist
        
    Returns:
        JSON Object with result of the operation
    """
    try:
        # Get analyzer instance from price updater
        if price_updater is None:
            return {"success": False, "message": "Price updater not initialized"}
            
        ad_id = data.get("ad_id")
        if not ad_id:
            return {"success": False, "message": "Ad ID is required"}
            
        analyzer = price_updater.ml_analyzer
        analyzer.blacklist_ads([ad_id])
        
        return {
            "success": True,
            "message": f"Ad {ad_id} added to blacklist",
            "blacklisted_count": len(analyzer.blacklisted_ads)
        }
    except Exception as e:
        logger.error(f"Error blacklisting ad: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/api/blacklist/list")
async def get_blacklists():
    """
    Get the current blacklists
    
    Returns:
        JSON Object with blacklisted advertisers and ads
    """
    try:
        # Get analyzer instance from price updater
        if price_updater is None:
            return {"success": False, "message": "Price updater not initialized"}
            
        analyzer = price_updater.ml_analyzer
        
        return {
            "success": True,
            "restricted_advertisers": list(analyzer.restricted_advertisers),
            "blacklisted_ads": list(analyzer.blacklisted_ads)
        }
    except Exception as e:
        logger.error(f"Error getting blacklists: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/api/blacklist/unban-advertiser")
async def unban_advertiser(data: Dict[str, Any]):
    """
    Remove an advertiser from the restricted list
    
    Request Body:
        advertiser_id: ID of the advertiser to unban
        
    Returns:
        JSON Object with result of the operation
    """
    try:
        # Get analyzer instance from price updater
        if price_updater is None:
            return {"success": False, "message": "Price updater not initialized"}
            
        advertiser_id = data.get("advertiser_id")
        if not advertiser_id:
            return {"success": False, "message": "Advertiser ID is required"}
            
        analyzer = price_updater.ml_analyzer
        
        # Remove the advertiser ID from the restricted set
        if advertiser_id in analyzer.restricted_advertisers:
            analyzer.restricted_advertisers.remove(advertiser_id)
            logger.info(f"Removed advertiser {advertiser_id} from restricted list")
        
        return {
            "success": True,
            "message": f"Advertiser {advertiser_id} removed from restricted list",
            "restricted_count": len(analyzer.restricted_advertisers)
        }
    except Exception as e:
        logger.error(f"Error unbanning advertiser: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/api/blacklist/unban-ad")
async def unban_ad(data: Dict[str, Any]):
    """
    Remove an ad from the blacklist
    
    Request Body:
        ad_id: ID of the ad to unban
        
    Returns:
        JSON Object with result of the operation
    """
    try:
        # Get analyzer instance from price updater
        if price_updater is None:
            return {"success": False, "message": "Price updater not initialized"}
            
        ad_id = data.get("ad_id")
        if not ad_id:
            return {"success": False, "message": "Ad ID is required"}
            
        analyzer = price_updater.ml_analyzer
        
        # Remove the ad ID from the blacklist set
        if ad_id in analyzer.blacklisted_ads:
            analyzer.blacklisted_ads.remove(ad_id)
            logger.info(f"Removed ad {ad_id} from blacklist")
        
        return {
            "success": True,
            "message": f"Ad {ad_id} removed from blacklist",
            "blacklisted_count": len(analyzer.blacklisted_ads)
        }
    except Exception as e:
        logger.error(f"Error unblacklisting ad: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    try:
        stop_price_updater()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")