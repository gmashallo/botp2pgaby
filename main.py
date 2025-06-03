from flask import Flask, jsonify, request, render_template
import time
import logging
import atexit

from app.utils import make_binance_request
from app.config import get_settings
from app.price_updater import start_price_updater, stop_price_updater, price_updater

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# Create a Flask app
app = Flask(__name__)

# Enum for ad types
class AdType:
    BUY = "BUY"
    SELL = "SELL"

@app.route('/')
def root():
    """Root endpoint to render the UI for testing the API"""
    return render_template('index.html')

@app.route('/api/top-price')
def get_top_price():
    """
    Fetches top prices for USDT/TZS ads from Binance C2C market.
    
    Query Parameters:
        ad_type: Type of ad (BUY or SELL). If not provided, returns both.
    
    Returns:
        JSON Object containing top prices and trader nicknames
    """
    # Get ad_type from query parameters
    ad_type = request.args.get('ad_type')
    settings = get_settings()
    
    # Define base parameters for Binance API request
    base_params = {
        "fiat": "TZS",
        "asset": "USDT",
        "rows": 10,
        "page": 1,
        "timestamp": int(time.time() * 1000)
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
            params = {**base_params, "tradeType": type_value}
            
            # Make request to Binance API
            response = make_binance_request(
                endpoint="/sapi/v1/c2c/ads/search",
                params=params,
                api_key=settings.api_key,
                api_secret=settings.api_secret
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
                
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Error fetching top prices from Binance: {str(e)}"}), 500

@app.route('/api/release-order', methods=['POST'])
def release_order():
    """
    Releases crypto to the buyer after confirming payment received
    
    Request Body:
        order_number: The C2C order number to release
        
    Returns:
        JSON Object containing the result of the release operation
    """
    settings = get_settings()
    
    try:
        # Get JSON data from request
        data = request.get_json(force=True) if request.is_json else {}
        if not data:
            return jsonify({
                "error": "Invalid JSON payload"
            }), 400
            
        # Extract required fields from request
        order_number = data.get('order_number')
        
        # Validate required fields
        if not order_number:
            return jsonify({
                "error": "Missing required field: order_number is required"
            }), 400
        
        # Build parameters for Binance API
        params = {
            "orderNumber": str(order_number),
            "timestamp": int(time.time() * 1000)
        }
            
        # Make POST request to Binance API to release crypto
        response = make_binance_request(
            endpoint="/sapi/v1/c2c/orderMatch/releaseCoin",
            params=params,
            api_key=settings.api_key,
            api_secret=settings.api_secret,
            method="POST"
        )
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error releasing order: {str(e)}")
        return jsonify({"error": f"Error releasing order: {str(e)}"}), 500

@app.route('/api/post-ad', methods=['POST'])
def post_ad():
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
        # Get JSON data from request
        data = request.get_json(force=True) if request.is_json else {}
        if not data:
            return jsonify({
                "error": "Invalid JSON payload"
            }), 400
            
        # Extract required fields from request
        price = data.get('price')
        quantity = data.get('quantity')
        trade_type = data.get('trade_type')
        
        # Validate required fields
        if not all([price, quantity, trade_type]):
            return jsonify({
                "error": "Missing required fields: price, quantity, and trade_type are required"
            }), 400
            
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
                return jsonify({
                    "error": f"Invalid pay_type: {pay_type}. Valid options are: {', '.join(valid_pay_types)}"
                }), 400
                
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
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error posting ad: {str(e)}")
        return jsonify({"error": f"Error posting ad to Binance: {str(e)}"}), 500

@app.route('/api/leaderboard')
def get_leaderboard():
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
    
    # Get query parameters
    sort_by = request.args.get('sort_by', 'volume').lower()
    asset = request.args.get('asset', 'USDT')
    fiat = request.args.get('fiat', 'TZS')
    trade_type = request.args.get('trade_type')
    days = int(request.args.get('days', 30))
    
    if sort_by not in ['volume', 'orders']:
        return jsonify({
            "error": "Invalid sort_by parameter. Valid options are 'volume' or 'orders'."
        }), 400
    
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
            
            return jsonify({
                "sort_by": sort_by,
                "days": days,
                "count": len(top_traders),
                "traders": top_traders
            })
        else:
            return jsonify({
                "error": "No order data returned from Binance"
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        return jsonify({"error": f"Error fetching leaderboard: {str(e)}"}), 500

# Price updater status and controls
@app.route('/api/price-updater/status')
def get_updater_status():
    """
    Get the current status of the price updater
    
    Returns:
        JSON object with status information
    """
    status = "running" if price_updater and price_updater.running else "stopped"
    interval = price_updater.interval if price_updater else 30
    
    return jsonify({
        "status": status,
        "interval": interval,
        "updater_active": price_updater is not None
    })

@app.route('/api/price-updater/start', methods=['POST'])
def start_updater():
    """
    Start the price updater
    
    Returns:
        JSON object with result
    """
    try:
        # Get interval from request if provided
        data = request.get_json(force=True) if request.is_json else {}
        interval = data.get('interval', 30)
        
        if not isinstance(interval, int) or interval < 5:
            return jsonify({
                "success": False, 
                "message": "Interval must be an integer of at least 5 seconds"
            }), 400
            
        start_price_updater(interval=interval)
        
        return jsonify({
            "success": True,
            "message": f"Price updater started with interval {interval} seconds"
        })
        
    except Exception as e:
        logger.error(f"Error starting price updater: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error starting price updater: {str(e)}"
        }), 500

@app.route('/api/price-updater/stop', methods=['POST'])
def stop_updater():
    """
    Stop the price updater
    
    Returns:
        JSON object with result
    """
    try:
        stop_price_updater()
        
        return jsonify({
            "success": True,
            "message": "Price updater stopped"
        })
        
    except Exception as e:
        logger.error(f"Error stopping price updater: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error stopping price updater: {str(e)}"
        }), 500

def initialize_app():
    """
    Initialize the application
    """
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

# Register app initialization on startup
# Initialize app when it starts
with app.app_context():
    initialize_app()

# Register cleanup on shutdown
@atexit.register
def on_shutdown():
    stop_price_updater()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
