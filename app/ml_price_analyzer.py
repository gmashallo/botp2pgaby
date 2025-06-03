"""
Machine Learning Price Analyzer for Binance C2C Trading

This module uses machine learning to analyze and filter Binance C2C ads:
1. Detect and filter out bot-driven advertisers
2. Ignore restricted advertisers based on configurable criteria
3. Apply intelligent price adjustment strategies
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import joblib
import logging
import os
import time
from typing import List, Dict, Any, Tuple, Optional, Union
import datetime

# Configure logging
logger = logging.getLogger(__name__)

class MLPriceAnalyzer:
    """
    Machine Learning Price Analyzer for P2P trading price optimization
    """
    def __init__(self):
        """Initialize the ML price analyzer"""
        self.model_path = "models/advertiser_model.joblib"
        self.anomaly_detector = None
        self.clustering_model = None
        self.scaler = StandardScaler()
        self.historical_data = []
        self.bot_advertisers = set()
        self.restricted_advertisers = set()
        self.blacklisted_ads = set()  # Store ad IDs to blacklist
        self.last_trained = None
        self.training_frequency = 24 * 60 * 60  # Train every 24 hours
        self.min_data_points = 10
        
        # Default limit filters
        self.min_limit_filter = 0  # Minimum transaction limit
        self.max_limit_filter = float('inf')  # Maximum transaction limit
        self.min_available_filter = 0  # Minimum available amount
        self.min_completion_rate = 0  # Minimum completion rate (%)
        self.min_order_count = 0  # Minimum order count
        
        # Create models directory if it doesn't exist
        os.makedirs("models", exist_ok=True)
        
        # Try to load existing model
        self._load_model()
    
    def _load_model(self) -> bool:
        """
        Load trained ML model if it exists
        
        Returns:
            bool: True if model was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.model_path):
                self.anomaly_detector = joblib.load(self.model_path)
                logger.info("Loaded existing ML model")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading ML model: {str(e)}")
            return False
    
    def _save_model(self) -> bool:
        """
        Save trained ML model
        
        Returns:
            bool: True if model was saved successfully, False otherwise
        """
        try:
            joblib.dump(self.anomaly_detector, self.model_path)
            logger.info("Saved ML model")
            return True
        except Exception as e:
            logger.error(f"Error saving ML model: {str(e)}")
            return False
    
    def process_ads(self, ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process list of ads: filter bots, restricted advertisers, and apply ML filtering
        
        Args:
            ads: List of ad data from Binance API
            
        Returns:
            Filtered list of ads
        """
        if not ads:
            return []
        
        # Store for training
        self.historical_data.extend(ads)
        
        # Check if we need to train
        self._check_train_model()
        
        # Convert ads to DataFrame for easier processing
        processed_ads = self._preprocess_ads(ads)
        
        # Filter out known bots and restricted advertisers
        filtered_ads = self._filter_known_bad_advertisers(processed_ads)
        
        # Apply ML-based filtering if model exists
        if self.anomaly_detector is not None:
            filtered_ads = self._apply_ml_filtering(filtered_ads)
        
        # Convert back to original format
        result = self._postprocess_ads(filtered_ads, ads)
        
        logger.info(f"Processed {len(ads)} ads, {len(result)} remain after filtering")
        return result
    
    def _preprocess_ads(self, ads: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert raw ads data to DataFrame with extracted features
        
        Args:
            ads: List of ad data from Binance API
            
        Returns:
            DataFrame with extracted features
        """
        # Extract key features for analysis
        records = []
        
        for ad in ads:
            try:
                # Skip ads without proper structure
                if not ad.get('adv', {}) or not ad.get('adv', {}).get('advertiser', {}):
                    continue
                
                adv = ad['adv']
                advertiser = adv.get('advertiser', {})
                
                record = {
                    'advertiser_id': advertiser.get('userNo', ''),
                    'nickname': advertiser.get('nickName', ''),
                    'price': float(adv.get('price', 0)),
                    'available': float(adv.get('surplusAmount', 0)),
                    'min_limit': float(adv.get('minSingleTransAmount', 0)),
                    'max_limit': float(adv.get('maxSingleTransAmount', 0)),
                    'trade_count': int(advertiser.get('monthOrderCount', 0)),
                    'completion_rate': float(advertiser.get('monthFinishRate', 0)) * 100,
                    'timestamp': time.time()
                }
                
                records.append(record)
            except Exception as e:
                logger.warning(f"Error processing ad: {str(e)}")
                continue
        
        if not records:
            return pd.DataFrame()
        
        return pd.DataFrame(records)
    
    def _filter_known_bad_advertisers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter out known bots, restricted advertisers, blacklisted ads,
        and apply transaction limit filters
        
        Args:
            df: DataFrame of preprocessed ads
            
        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df
            
        # Filter out known bot advertisers
        if self.bot_advertisers:
            mask = ~df['advertiser_id'].isin(list(self.bot_advertisers))
            df = df[mask].copy()
        
        # Filter out restricted advertisers
        if self.restricted_advertisers:
            mask = ~df['advertiser_id'].isin(list(self.restricted_advertisers))
            df = df[mask].copy()
            
        # Filter out blacklisted ad IDs
        if self.blacklisted_ads:
            mask = ~df['ad_id'].isin(list(self.blacklisted_ads))
            df = df[mask].copy()
        
        # Apply limit filters
        mask = (
            (df['min_limit'] >= self.min_limit_filter) & 
            (df['max_limit'] <= self.max_limit_filter if self.max_limit_filter < float('inf') else True) &
            (df['available'] >= self.min_available_filter) &
            (df['completion_rate'] >= self.min_completion_rate) &
            (df['trade_count'] >= self.min_order_count)
        )
        df = df[mask].copy()
        
        return df
    
    def _apply_ml_filtering(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply machine learning filtering
        
        Args:
            df: DataFrame of preprocessed ads
            
        Returns:
            Filtered DataFrame with anomalies removed
        """
        if df.empty or self.anomaly_detector is None:
            return df
            
        try:
            # Extract numeric features for anomaly detection
            features = df[['price', 'available', 'min_limit', 'max_limit', 
                          'trade_count', 'completion_rate']].copy()
            
            # Handle missing values
            features.fillna(0, inplace=True)
            
            # Scale features
            scaled_features = self.scaler.transform(features)
            
            # Predict anomalies (-1 for outliers, 1 for normal)
            predictions = self.anomaly_detector.predict(scaled_features)
            
            # Filter out anomalies
            normal_indices = predictions == 1
            normal_df = df.iloc[normal_indices].copy()
            
            # Track bot advertisers from anomalies
            anomaly_indices = predictions == -1
            if anomaly_indices.any():
                new_bots = set(df.iloc[anomaly_indices]['advertiser_id'].tolist())
                self.bot_advertisers.update(new_bots)
                logger.info(f"Added {len(new_bots)} new bot advertisers to filter list")
            
            return normal_df
            
        except Exception as e:
            logger.error(f"Error in ML filtering: {str(e)}")
            return df
    
    def _postprocess_ads(self, filtered_df: pd.DataFrame, original_ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert filtered DataFrame back to original format
        
        Args:
            filtered_df: DataFrame after filtering
            original_ads: Original list of ads
            
        Returns:
            Filtered list in original format
        """
        if filtered_df.empty:
            return []
            
        # Get list of approved advertiser IDs
        approved_ids = set(filtered_df['advertiser_id'].tolist())
        
        # Filter original list
        filtered_ads = []
        for ad in original_ads:
            try:
                advertiser_id = ad.get('adv', {}).get('advertiser', {}).get('userNo', '')
                if advertiser_id in approved_ids:
                    filtered_ads.append(ad)
            except Exception:
                continue
        
        return filtered_ads
    
    def _check_train_model(self):
        """Check if model should be trained and train if needed"""
        # Only train if we have enough data
        if len(self.historical_data) < self.min_data_points:
            return
            
        # Check if enough time has passed since last training
        current_time = time.time()
        if (self.last_trained is None or 
            (current_time - self.last_trained) > self.training_frequency):
            
            self._train_model()
            self.last_trained = current_time
    
    def _train_model(self):
        """Train machine learning model on collected historical data"""
        # Convert to DataFrame
        all_df = self._preprocess_ads(self.historical_data)
        
        if all_df.empty or len(all_df) < self.min_data_points:
            logger.warning("Not enough data to train model")
            return
        
        try:
            logger.info(f"Training ML model on {len(all_df)} data points")
            
            # Extract numeric features
            features = all_df[['price', 'available', 'min_limit', 'max_limit', 
                               'trade_count', 'completion_rate']].copy()
            
            # Handle missing values
            features.fillna(0, inplace=True)
            
            # Scale features
            self.scaler = StandardScaler()
            scaled_features = self.scaler.fit_transform(features)
            
            # Train Isolation Forest for anomaly detection
            self.anomaly_detector = IsolationForest(
                n_estimators=100,
                contamination="auto",  # Let the model decide contamination rate
                random_state=42
            )
            self.anomaly_detector.fit(scaled_features)
            
            # Save the model
            self._save_model()
            
            logger.info("ML model training completed")
            
        except Exception as e:
            logger.error(f"Error training ML model: {str(e)}")
    
    def flag_restricted_advertisers(self, advertiser_ids: List[str]):
        """
        Flag advertisers as restricted
        
        Args:
            advertiser_ids: List of advertiser IDs to restrict
        """
        self.restricted_advertisers.update(set(advertiser_ids))
        logger.info(f"Added {len(advertiser_ids)} advertisers to restricted list")
        
    def blacklist_ads(self, ad_ids: List[str]):
        """
        Blacklist specific ads by their IDs
        
        Args:
            ad_ids: List of ad IDs to blacklist
        """
        self.blacklisted_ads.update(set(ad_ids))
        logger.info(f"Added {len(ad_ids)} ads to blacklist")
        
    def set_limit_filters(self, 
                          min_limit: Optional[float] = None, 
                          max_limit: Optional[float] = None,
                          min_available: Optional[float] = None,
                          min_completion_rate: Optional[float] = None,
                          min_order_count: Optional[int] = None):
        """
        Set filters for transaction limits and other ad criteria
        
        Args:
            min_limit: Minimum transaction limit to consider (default: keep current)
            max_limit: Maximum transaction limit to consider (default: keep current)
            min_available: Minimum available amount (default: keep current)
            min_completion_rate: Minimum completion rate percentage (default: keep current)
            min_order_count: Minimum number of completed orders (default: keep current)
        """
        if min_limit is not None:
            self.min_limit_filter = float(min_limit)
            
        if max_limit is not None:
            self.max_limit_filter = float(max_limit)
            
        if min_available is not None:
            self.min_available_filter = float(min_available)
            
        if min_completion_rate is not None:
            self.min_completion_rate = float(min_completion_rate)
            
        if min_order_count is not None:
            self.min_order_count = int(min_order_count)
            
        logger.info(f"Updated limit filters: min_limit={self.min_limit_filter}, " 
                   f"max_limit={self.max_limit_filter}, min_available={self.min_available_filter}, "
                   f"min_completion_rate={self.min_completion_rate}, min_order_count={self.min_order_count}")
    
    def get_optimal_price(self, ads: List[Dict[str, Any]], trade_type: str, 
                          adjustment_percentage: float = 0.5) -> Optional[float]:
        """
        Calculate optimal price based on ML-filtered market data
        
        Args:
            ads: List of ads from Binance API
            trade_type: "BUY" or "SELL"
            adjustment_percentage: Percentage to adjust price (0.5 = 0.5%)
            
        Returns:
            Optimal price or None if can't determine
        """
        # Process ads with ML filtering
        filtered_ads = self.process_ads(ads)
        
        if not filtered_ads:
            logger.warning("No valid ads after filtering")
            return None
        
        try:
            # Extract prices
            prices = []
            for ad in filtered_ads:
                price_str = ad.get('adv', {}).get('price', '0')
                try:
                    price = float(price_str)
                    prices.append(price)
                except (ValueError, TypeError):
                    continue
            
            if not prices:
                return None
                
            # For BUY ads, we want to find the lowest price and beat it
            # For SELL ads, we want to find the highest price and beat it
            if trade_type == "BUY":
                base_price = min(prices)
                # For BUY ads, we want to offer a lower price (subtract adjustment)
                optimal_price = base_price * (1 - adjustment_percentage / 100)
            else:  # SELL
                base_price = max(prices)
                # For SELL ads, we want to offer a higher price (add adjustment)
                optimal_price = base_price * (1 + adjustment_percentage / 100)
                
            logger.info(f"Calculated optimal {trade_type} price: {optimal_price:.2f} "
                       f"(base: {base_price:.2f}, adj: {adjustment_percentage}%)")
                
            return optimal_price
            
        except Exception as e:
            logger.error(f"Error calculating optimal price: {str(e)}")
            return None