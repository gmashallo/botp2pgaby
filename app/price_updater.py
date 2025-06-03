import time
import threading
import logging
import os
from typing import Dict, Any, List, Optional

from app.utils import make_binance_request
from app.config import get_settings
from app.ml_price_analyzer import MLPriceAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("price_updater")

class PriceUpdater:
    """
    A class to periodically check top traders' prices and adjust existing ads
    """
    def __init__(self, interval: int = 30):
        """
        Initialize the price updater
        
        Args:
            interval: Time interval in seconds between price checks
        """
        self.interval = interval
        self.settings = get_settings()
        self.running = False
        self.thread = None
        self.price_margin = 0.01  # 1% margin to stay competitive
        
        # Create ML price analyzer instance
        self.ml_analyzer = MLPriceAnalyzer()
        
    def get_my_ads(self) -> List[Dict[str, Any]]:
        """
        Get all of my active ads from Binance
        
        Returns:
            List of ad objects
        """
        try:
            params = {
                "timestamp": int(time.time() * 1000)
            }
            
            response = make_binance_request(
                endpoint="/sapi/v1/c2c/ads/list-user-ads",
                params=params,
                api_key=self.settings.api_key,
                api_secret=self.settings.api_secret
            )
            
            # Filter only active ads
            if "data" in response:
                return [ad for ad in response["data"] if ad.get("status") == "ONLINE"]
            return []
            
        except Exception as e:
            logger.error(f"Error fetching my ads: {str(e)}")
            return []
            
    def get_top_price(self, asset: str, fiat: str, trade_type: str) -> Optional[float]:
        """
        Get the top price for a specific asset/fiat pair and trade type using ML-based filtering
        
        Args:
            asset: Crypto asset (e.g., USDT)
            fiat: Fiat currency (e.g., TZS)
            trade_type: BUY or SELL
            
        Returns:
            Top price or None if not found
        """
        try:
            params = {
                "asset": asset,
                "fiat": fiat,
                "tradeType": trade_type,
                "rows": 20,  # Get more rows to have enough data for ML filtering
                "page": 1,
                "timestamp": int(time.time() * 1000)
            }
            
            response = make_binance_request(
                endpoint="/sapi/v1/c2c/ads/search",
                params=params,
                api_key=self.settings.api_key,
                api_secret=self.settings.api_secret
            )
            
            # Extract ads
            if "data" in response and response["data"]:
                ads = response["data"]
                
                # Get my nickname to filter out my own ads
                my_nickname = self.get_my_nickname()
                
                # Pre-filter my own ads before ML processing
                filtered_ads = [
                    ad for ad in ads 
                    if ad.get("adv", {}).get("advertiser", {}).get("nickName") != my_nickname
                ]
                
                # Let ML analyzer determine the optimal price
                optimal_price = self.ml_analyzer.get_optimal_price(
                    filtered_ads, 
                    trade_type,
                    adjustment_percentage=0.5  # 0.5% adjustment
                )
                
                if optimal_price is not None:
                    logger.info(f"ML analyzer determined optimal {trade_type} price: {optimal_price}")
                    return optimal_price
                
                # Fallback to traditional method if ML can't determine
                logger.info("Falling back to traditional price selection")
                # Sort by price (ascending for BUY, descending for SELL)
                if trade_type == "BUY":
                    # For BUY ads, buyers want lowest price
                    sorted_ads = sorted(filtered_ads, key=lambda x: float(x.get("adv", {}).get("price", 0)))
                else:  # SELL
                    # For SELL ads, sellers want highest price
                    sorted_ads = sorted(filtered_ads, key=lambda x: float(x.get("adv", {}).get("price", 0)), reverse=True)
                
                if sorted_ads:
                    return float(sorted_ads[0].get("adv", {}).get("price", 0))
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching top price: {str(e)}")
            return None
    
    def get_my_nickname(self) -> str:
        """
        Get my nickname from Binance
        
        Returns:
            Nickname string or empty string if not found
        """
        try:
            params = {
                "timestamp": int(time.time() * 1000)
            }
            
            response = make_binance_request(
                endpoint="/sapi/v1/c2c/user-info",
                params=params,
                api_key=self.settings.api_key,
                api_secret=self.settings.api_secret
            )
            
            if response and "data" in response:
                return response["data"].get("nickName", "")
            return ""
            
        except Exception as e:
            logger.error(f"Error fetching user info: {str(e)}")
            return ""
    
    def update_ad_price(self, ad_id: str, new_price: float) -> bool:
        """
        Update an ad's price
        
        Args:
            ad_id: ID of the ad to update
            new_price: New price to set
            
        Returns:
            Success status
        """
        try:
            params = {
                "advertiseId": ad_id,
                "price": str(new_price),
                "timestamp": int(time.time() * 1000)
            }
            
            response = make_binance_request(
                endpoint="/sapi/v1/c2c/ads/update",
                params=params,
                api_key=self.settings.api_key,
                api_secret=self.settings.api_secret,
                method="POST"
            )
            
            if response and response.get("success", False):
                logger.info(f"Successfully updated ad {ad_id} to new price: {new_price}")
                return True
            
            logger.warning(f"Failed to update ad {ad_id}. Response: {response}")
            return False
            
        except Exception as e:
            logger.error(f"Error updating ad price: {str(e)}")
            return False
    
    def calculate_competitive_price(self, top_price: float, trade_type: str) -> float:
        """
        Calculate a competitive price based on top price and trade type
        
        This is a fallback method when ML-based pricing is not available
        
        Args:
            top_price: The current top price
            trade_type: BUY or SELL
            
        Returns:
            Calculated competitive price
        """
        # Use smaller margin than ML-based pricing (0.5% instead of 1%)
        margin = 0.005
        
        if trade_type == "BUY":
            # For BUY ads, lower price is better (undercut by percentage margin)
            return round(top_price * (1 - margin), 2)
        else:  # SELL
            # For SELL ads, higher price is better (increase by percentage margin)
            return round(top_price * (1 + margin), 2)
    
    def check_and_update_prices(self):
        """
        Check top prices and update existing ads if needed
        """
        logger.info("Starting price check and update...")
        
        # Get my active ads
        my_ads = self.get_my_ads()
        if not my_ads:
            logger.info("No active ads found to update")
            return
        
        for ad in my_ads:
            try:
                # Extract ad details
                ad_id = ad.get("advId")
                asset = ad.get("asset")
                fiat = ad.get("fiat")
                trade_type = ad.get("tradeType")
                current_price = float(ad.get("price", 0))
                
                if not all([ad_id, asset, fiat, trade_type, current_price]):
                    logger.warning(f"Incomplete ad data, skipping: {ad}")
                    continue
                
                # Get top price for this asset/fiat pair and trade type
                # Type checking
                asset_str = str(asset)
                fiat_str = str(fiat)
                trade_type_str = str(trade_type)
                
                top_price = self.get_top_price(asset_str, fiat_str, trade_type_str)
                
                if top_price is None:
                    logger.info(f"No top price found for {asset}/{fiat} {trade_type}, skipping")
                    continue
                
                # Calculate competitive price
                new_price = self.calculate_competitive_price(top_price, trade_type_str)
                
                # Only update if the price difference is significant (>0.5%)
                price_diff_percent = abs(new_price - current_price) / current_price * 100
                if price_diff_percent < 0.5:
                    logger.info(f"Price difference too small ({price_diff_percent:.2f}%), not updating ad {ad_id}")
                    continue
                
                # Update the ad price
                logger.info(f"Updating {trade_type} ad {ad_id} from {current_price} to {new_price}")
                # Ensure ad_id is a string
                ad_id_str = str(ad_id)
                self.update_ad_price(ad_id_str, new_price)
                
            except Exception as e:
                logger.error(f"Error processing ad: {str(e)}")
    
    def update_loop(self):
        """
        Main loop for periodic price updates
        """
        while self.running:
            try:
                self.check_and_update_prices()
            except Exception as e:
                logger.error(f"Error in update loop: {str(e)}")
                
            # Sleep for the interval
            time.sleep(self.interval)
    
    def start(self):
        """
        Start the price updater in a background thread
        """
        if self.running:
            logger.warning("Price updater is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self.update_loop, daemon=True)
        self.thread.start()
        logger.info(f"Price updater started, checking every {self.interval} seconds")
    
    def stop(self):
        """
        Stop the price updater
        """
        if not self.running:
            logger.warning("Price updater is not running")
            return
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            logger.info("Price updater stopped")

# Global price updater instance
price_updater = None

def start_price_updater(interval: int = 30):
    """
    Start the global price updater
    
    Args:
        interval: Time interval in seconds between price checks
    """
    global price_updater
    
    if price_updater is None:
        price_updater = PriceUpdater(interval=interval)
    
    price_updater.start()
    
def stop_price_updater():
    """
    Stop the global price updater
    """
    global price_updater
    
    if price_updater is not None:
        price_updater.stop()