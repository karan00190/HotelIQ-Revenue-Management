import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict, List, Tuple
from datetime import datetime
from app.models.hotel import Booking, DailyMetrics
from app.services.data_validator import BookingDataValidator, DataQualityReport
from app.services.feature_engineering import FeatureEngineer


class ETLPipeline:
    """
    Orchestrates the ETL (Extract, Transform, Load) process for booking data.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.validator = BookingDataValidator()
        self.feature_engineer = FeatureEngineer()
    
    def extract_from_csv(self, file_path: str) -> pd.DataFrame:
        """
        Extract data from CSV file.
        """
        print(f"📥 Extracting data from: {file_path}")
        df = pd.read_csv(file_path)
        print(f"  ✅ Extracted {len(df)} records")
        return df
    
    def extract_from_database(self, hotel_id: int = None, start_date: str = None) -> pd.DataFrame:
        """
        Extract existing bookings from database.
        """
        print("📥 Extracting data from database...")
        query = self.db.query(Booking)
        
        if hotel_id:
            query = query.filter(Booking.hotel_id == hotel_id)
        
        if start_date:
            query = query.filter(Booking.check_in_date >= start_date)
        
        bookings = query.all()
        
        # Convert to DataFrame
        data = []
        for booking in bookings:
            data.append({
                'hotel_id': booking.hotel_id,
                'room_id': booking.room_id,
                'check_in_date': booking.check_in_date,
                'check_out_date': booking.check_out_date,
                'guest_name': booking.guest_name,
                'guest_email': booking.guest_email,
                'num_guests': booking.num_guests,
                'booking_price': booking.booking_price,
                'base_price': booking.base_price,
                'booking_date': booking.booking_date,
                'booking_source': booking.booking_source,
                'status': booking.status
            })
        
        df = pd.DataFrame(data)
        print(f"  ✅ Extracted {len(df)} records from database")
        return df
    
    def transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, DataQualityReport]:
        """
        Transform and validate data.
        """
        print("\n🔄 Starting transformation...")
        
        # Step 1: Validate
        print("  → Validating data quality...")
        report = self.validator.validate_dataframe(df)
        
        if not report.is_valid():
            print("  ❌ Validation failed!")
            return df, report
        
        # Step 2: Clean
        print("  → Cleaning data...")
        df_clean = self.validator.clean_dataframe(df)
        
        # Step 3: Feature Engineering
        print("  → Engineering features...")
        df_transformed = self.feature_engineer.create_all_features(df_clean, self.db)
        
        print("✅ Transformation complete!")
        return df_transformed, report
    
    def load_to_database(self, df: pd.DataFrame, batch_size: int = 100) -> Dict:
        """
        Load transformed data into database.
        """
        print("\n💾 Loading data to database...")
        
        loaded_count = 0
        skipped_count = 0
        error_count = 0
        
        # Select only columns that match Booking model
        booking_cols = [
            'hotel_id', 'room_id', 'check_in_date', 'check_out_date',
            'guest_name', 'guest_email', 'num_guests', 'booking_price',
            'base_price', 'booking_source', 'status'
        ]
        
        # Add booking_date if not present
        if 'booking_date' not in df.columns:
            df['booking_date'] = datetime.now()
        booking_cols.append('booking_date')
        
        df_to_load = df[booking_cols].copy()
        
        # Load in batches
        for i in range(0, len(df_to_load), batch_size):
            batch = df_to_load.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                try:
                    # Check if booking already exists
                    existing = self.db.query(Booking).filter(
                        Booking.hotel_id == row['hotel_id'],
                        Booking.room_id == row['room_id'],
                        Booking.check_in_date == row['check_in_date']
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Create new booking
                    booking = Booking(**row.to_dict())
                    self.db.add(booking)
                    loaded_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"  ⚠️  Error loading record: {str(e)}")
            
            # Commit batch
            try:
                self.db.commit()
                print(f"  ✅ Batch {i//batch_size + 1} committed ({loaded_count} loaded so far)")
            except Exception as e:
                self.db.rollback()
                print(f"  ❌ Batch commit failed: {str(e)}")
        
        result = {
            "loaded": loaded_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total": len(df_to_load)
        }
        
        print(f"\n✅ Load complete: {loaded_count} new records, {skipped_count} skipped, {error_count} errors")
        return result
    
    def run_full_pipeline(self, source: str, **kwargs) -> Dict:
        """
        Run complete ETL pipeline.
        
        Args:
            source: 'csv' or 'database'
            **kwargs: Additional arguments (file_path for CSV, filters for database)
        """
        print("=" * 60)
        print("🚀 Starting ETL Pipeline")
        print("=" * 60)
        
        start_time = datetime.now()
        
        # Extract
        if source == 'csv':
            df = self.extract_from_csv(kwargs.get('file_path'))
        elif source == 'database':
            df = self.extract_from_database(
                hotel_id=kwargs.get('hotel_id'),
                start_date=kwargs.get('start_date')
            )
        else:
            raise ValueError("Source must be 'csv' or 'database'")
        
        # Transform
        df_transformed, validation_report = self.transform(df)
        
        if not validation_report.is_valid():
            return {
                "success": False,
                "validation_report": validation_report.to_dict(),
                "message": "Pipeline failed at validation stage"
            }
        
        # Load
        load_result = self.load_to_database(df_transformed)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Feature summary
        feature_summary = self.feature_engineer.get_feature_summary(df_transformed)
        
        print("=" * 60)
        print(f"✅ ETL Pipeline Complete! Duration: {duration:.2f}s")
        print("=" * 60)
        
        return {
            "success": True,
            "duration_seconds": duration,
            "validation_report": validation_report.to_dict(),
            "load_result": load_result,
            "feature_summary": feature_summary,
            "message": "ETL pipeline completed successfully"
        }