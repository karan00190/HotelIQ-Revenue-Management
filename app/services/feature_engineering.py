import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models.hotel import Booking, Hotel, Room


class FeatureEngineer:
    """
    Creates ML features from raw booking data.
    Features are used for demand forecasting and pricing models.
    """
    
    @staticmethod
    def create_time_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Create time-based features from check-in dates.
        """
        df = df.copy()
        
        # Basic time features
        df['day_of_week'] = df['check_in_date'].dt.dayofweek  # 0=Monday, 6=Sunday
        df['day_of_month'] = df['check_in_date'].dt.day
        df['month'] = df['check_in_date'].dt.month
        df['quarter'] = df['check_in_date'].dt.quarter
        df['year'] = df['check_in_date'].dt.year
        df['week_of_year'] = df['check_in_date'].dt.isocalendar().week
        
        # Weekend flag
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Season (Indian context)
        df['season'] = df['month'].map({
            12: 'winter', 1: 'winter', 2: 'winter',
            3: 'spring', 4: 'spring', 5: 'spring',
            6: 'monsoon', 7: 'monsoon', 8: 'monsoon',
            9: 'autumn', 10: 'autumn', 11: 'autumn'
        })
        
        # Peak season flag (Oct-Feb)
        df['is_peak_season'] = df['month'].isin([10, 11, 12, 1, 2]).astype(int)
        
        # Holiday proximity (approximate - can be enhanced)
        df['is_holiday_season'] = df['month'].isin([12, 1, 4, 10]).astype(int)
        
        return df
    
    @staticmethod
    def create_stay_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Create features related to length of stay.
        """
        df = df.copy()
        
        # Length of stay
        df['length_of_stay'] = (df['check_out_date'] - df['check_in_date']).dt.days
        
        # Stay category
        df['stay_category'] = pd.cut(
            df['length_of_stay'],
            bins=[0, 1, 3, 7, 30],
            labels=['short', 'medium', 'long', 'extended']
        )
        
        # Lead time (days between booking and check-in)
        if 'booking_date' in df.columns:
            df['lead_time_days'] = (df['check_in_date'] - df['booking_date']).dt.days
            df['is_last_minute'] = (df['lead_time_days'] <= 3).astype(int)
        
        return df
    
    @staticmethod
    def create_pricing_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Create pricing-related features.
        """
        df = df.copy()
        
        # Price per night
        df['price_per_night'] = df['booking_price'] / df['length_of_stay']
        
        # Discount percentage
        df['discount_pct'] = ((df['base_price'] - df['booking_price']) / df['base_price'] * 100).clip(lower=0)
        
        # Price category
        df['price_category'] = pd.cut(
            df['price_per_night'],
            bins=[0, 3000, 6000, 10000, np.inf],
            labels=['budget', 'mid_range', 'premium', 'luxury']
        )
        
        return df
    
    @staticmethod
    def create_aggregated_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Create rolling window and aggregated features.
        """
        df = df.copy()
        df = df.sort_values('check_in_date')
        
        # Rolling features (7-day and 30-day windows)
        for window in [7, 30]:
            # Average price in window
            df[f'avg_price_{window}d'] = df.groupby('hotel_id')['booking_price'].transform(
                lambda x: x.rolling(window=window, min_periods=1).mean()
            )
            
            # Booking count in window
            df[f'booking_count_{window}d'] = df.groupby('hotel_id')['booking_price'].transform(
                lambda x: x.rolling(window=window, min_periods=1).count()
            )
        
        # Lag features (previous booking prices)
        df['prev_booking_price'] = df.groupby(['hotel_id', 'room_id'])['booking_price'].shift(1)
        
        return df
    
    @staticmethod
    def create_occupancy_features(df: pd.DataFrame, db: Session) -> pd.DataFrame:
        """
        Create occupancy-related features by calculating hotel utilization.
        """
        df = df.copy()
        
        # Get total rooms per hotel
        hotels = db.query(Hotel.id, Hotel.total_rooms).all()
        hotel_rooms = {h.id: h.total_rooms for h in hotels}
        
        df['hotel_total_rooms'] = df['hotel_id'].map(hotel_rooms)
        
        # Calculate daily occupancy rate
        daily_bookings = df.groupby(['hotel_id', 'check_in_date']).size().reset_index(name='rooms_booked')
        daily_bookings['total_rooms'] = daily_bookings['hotel_id'].map(hotel_rooms)
        daily_bookings['occupancy_rate'] = (daily_bookings['rooms_booked'] / daily_bookings['total_rooms'] * 100).round(2)
        
        # Merge back
        df = df.merge(
            daily_bookings[['hotel_id', 'check_in_date', 'occupancy_rate']],
            on=['hotel_id', 'check_in_date'],
            how='left'
        )
        
        return df
    
    @staticmethod
    def create_all_features(df: pd.DataFrame, db: Session = None) -> pd.DataFrame:
        """
        Create all features in one pipeline.
        """
        print("🔧 Starting feature engineering...")
        
        # Time features
        df = FeatureEngineer.create_time_features(df)
        print("  ✅ Time features created")
        
        # Stay features
        df = FeatureEngineer.create_stay_features(df)
        print("  ✅ Stay features created")
        
        # Pricing features
        df = FeatureEngineer.create_pricing_features(df)
        print("  ✅ Pricing features created")
        
        # Aggregated features
        df = FeatureEngineer.create_aggregated_features(df)
        print("  ✅ Aggregated features created")
        
        # Occupancy features (requires database)
        if db:
            df = FeatureEngineer.create_occupancy_features(df, db)
            print("  ✅ Occupancy features created")
        
        print(f"✅ Feature engineering complete! Total features: {len(df.columns)}")
        
        return df
    
    @staticmethod
    def get_feature_summary(df: pd.DataFrame) -> Dict:
        """
        Get summary of engineered features.
        """
        feature_groups = {
            "time_features": [col for col in df.columns if col in [
                'day_of_week', 'month', 'quarter', 'is_weekend', 'season', 'is_peak_season'
            ]],
            "stay_features": [col for col in df.columns if col in [
                'length_of_stay', 'stay_category', 'lead_time_days', 'is_last_minute'
            ]],
            "pricing_features": [col for col in df.columns if col in [
                'price_per_night', 'discount_pct', 'price_category'
            ]],
            "aggregated_features": [col for col in df.columns if 'avg_price' in col or 'booking_count' in col],
            "occupancy_features": [col for col in df.columns if 'occupancy' in col]
        }
        
        return {
            "total_features": len(df.columns),
            "feature_groups": {k: len(v) for k, v in feature_groups.items()},
            "feature_list": feature_groups
        }