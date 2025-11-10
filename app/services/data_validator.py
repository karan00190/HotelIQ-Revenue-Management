from typing import Dict, List, Tuple
from datetime import datetime, date
import pandas as pd
from pydantic import ValidationError


class DataQualityReport:
    """Data quality report container"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.stats: Dict = {}
    
    def add_error(self, message: str):
        self.errors.append(message)
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def add_info(self, message: str):
        self.info.append(message)
    
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid(),
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "statistics": self.stats
        }


class BookingDataValidator:
    """Validates booking data for quality and consistency"""
    
    REQUIRED_COLUMNS = [
        'hotel_id', 'room_id', 'check_in_date', 'check_out_date',
        'guest_name', 'num_guests', 'booking_price', 'base_price'
    ]
    
    OPTIONAL_COLUMNS = [
        'guest_email', 'booking_source', 'status', 'booking_date'
    ]
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> DataQualityReport:
        """
        Comprehensive validation of booking DataFrame.
        """
        report = DataQualityReport()
        
        # Check 1: Required columns
        missing_cols = set(BookingDataValidator.REQUIRED_COLUMNS) - set(df.columns)
        if missing_cols:
            report.add_error(f"Missing required columns: {missing_cols}")
            return report
        
        report.add_info(f"All required columns present. Total rows: {len(df)}")
        
        # Check 2: Empty DataFrame
        if df.empty:
            report.add_error("DataFrame is empty")
            return report
        
        # Check 3: Null values in critical columns
        null_counts = df[BookingDataValidator.REQUIRED_COLUMNS].isnull().sum()
        for col, count in null_counts.items():
            if count > 0:
                report.add_error(f"Column '{col}' has {count} null values")
        
        # Check 4: Data types
        try:
            df['check_in_date'] = pd.to_datetime(df['check_in_date'])
            df['check_out_date'] = pd.to_datetime(df['check_out_date'])
        except Exception as e:
            report.add_error(f"Date conversion error: {str(e)}")
        
        # Check 5: Logical validations
        invalid_dates = df[df['check_out_date'] <= df['check_in_date']]
        if len(invalid_dates) > 0:
            report.add_error(f"{len(invalid_dates)} bookings have check-out before/same as check-in")
        
        # Check 6: Price validations
        invalid_prices = df[(df['booking_price'] <= 0) | (df['base_price'] <= 0)]
        if len(invalid_prices) > 0:
            report.add_error(f"{len(invalid_prices)} bookings have invalid prices (<=0)")
        
        # Check 7: Guest count validation
        invalid_guests = df[df['num_guests'] <= 0]
        if len(invalid_guests) > 0:
            report.add_error(f"{len(invalid_guests)} bookings have invalid guest count")
        
        # Check 8: Duplicate detection
        duplicates = df.duplicated(subset=['hotel_id', 'room_id', 'check_in_date'], keep=False)
        if duplicates.any():
            report.add_warning(f"{duplicates.sum()} potential duplicate bookings detected")
        
        # Check 9: Outlier detection (prices)
        price_mean = df['booking_price'].mean()
        price_std = df['booking_price'].std()
        outliers = df[df['booking_price'] > price_mean + (3 * price_std)]
        if len(outliers) > 0:
            report.add_warning(f"{len(outliers)} bookings with unusually high prices")
        
        # Statistics
        report.stats = {
            "total_records": len(df),
            "date_range": {
                "earliest": df['check_in_date'].min().isoformat() if not df['check_in_date'].isnull().all() else None,
                "latest": df['check_out_date'].max().isoformat() if not df['check_out_date'].isnull().all() else None
            },
            "price_stats": {
                "min": float(df['booking_price'].min()),
                "max": float(df['booking_price'].max()),
                "mean": float(df['booking_price'].mean()),
                "median": float(df['booking_price'].median())
            },
            "unique_hotels": int(df['hotel_id'].nunique()),
            "unique_rooms": int(df['room_id'].nunique())
        }
        
        if report.is_valid():
            report.add_info("✅ Data validation passed")
        
        return report
    
    @staticmethod
    def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize DataFrame.
        """
        df_clean = df.copy()
        
        # Convert dates
        df_clean['check_in_date'] = pd.to_datetime(df_clean['check_in_date'])
        df_clean['check_out_date'] = pd.to_datetime(df_clean['check_out_date'])
        
        # Fill optional columns with defaults
        if 'booking_source' not in df_clean.columns:
            df_clean['booking_source'] = 'direct'
        
        if 'status' not in df_clean.columns:
            df_clean['status'] = 'confirmed'
        
        if 'booking_date' not in df_clean.columns:
            df_clean['booking_date'] = datetime.now()
        
        # Strip whitespace from string columns
        string_cols = df_clean.select_dtypes(include=['object']).columns
        for col in string_cols:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].str.strip()
        
        # Remove duplicates
        df_clean = df_clean.drop_duplicates(
            subset=['hotel_id', 'room_id', 'check_in_date'],
            keep='first'
        )
        
        return df_clean