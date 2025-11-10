from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict
import pandas as pd
import io
from datetime import datetime

from app.database.connection import get_db
from app.services.etl_pipeline import ETLPipeline
from app.utils.metrics_calculator import MetricsCalculator

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion"])


@router.post("/upload-csv")
async def upload_csv_bookings(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV file with booking data.
    Runs complete ETL pipeline: validation, transformation, loading.
    
    **CSV Format Required:**
    - hotel_id, room_id, check_in_date, check_out_date
    - guest_name, num_guests, booking_price, base_price
    - Optional: guest_email, booking_source, status
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted"
        )
    
    try:
        # Read CSV from upload
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Save temporarily (optional - for debugging)
        temp_path = f"data/uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        df.to_csv(temp_path, index=False)
        
        # Run ETL pipeline
        pipeline = ETLPipeline(db)
        result = pipeline.run_full_pipeline(source='csv', file_path=temp_path)
        
        return {
            "filename": file.filename,
            "uploaded_at": datetime.now().isoformat(),
            "pipeline_result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing CSV: {str(e)}"
        )


@router.post("/process-existing-data")
def process_existing_bookings(
    hotel_id: int = None,
    start_date: str = None,
    db: Session = Depends(get_db)
):
    """
    Process existing bookings from database through ETL pipeline.
    Useful for re-engineering features on historical data.
    
    **Parameters:**
    - hotel_id: Optional - filter by specific hotel
    - start_date: Optional - filter bookings from this date (YYYY-MM-DD)
    """
    try:
        pipeline = ETLPipeline(db)
        result = pipeline.run_full_pipeline(
            source='database',
            hotel_id=hotel_id,
            start_date=start_date
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing data: {str(e)}"
        )


@router.post("/calculate-metrics")
def calculate_daily_metrics(
    hotel_id: int,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    """
    Calculate daily metrics (occupancy, revenue, ADR, RevPAR) for a date range.
    
    **Parameters:**
    - hotel_id: Hotel to calculate metrics for
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    """
    try:
        from datetime import datetime
        
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        metrics = MetricsCalculator.calculate_date_range_metrics(
            db=db,
            hotel_id=hotel_id,
            start_date=start,
            end_date=end
        )
        
        return {
            "hotel_id": hotel_id,
            "date_range": f"{start_date} to {end_date}",
            "metrics_calculated": len(metrics),
            "message": "Daily metrics calculated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating metrics: {str(e)}"
        )


@router.post("/recalculate-all-metrics")
def recalculate_all_metrics(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Recalculate all daily metrics for all hotels.
    This runs in the background to avoid timeout.
    
    **Warning:** This can take several minutes for large datasets.
    """
    try:
        # Run in background
        background_tasks.add_task(
            MetricsCalculator.recalculate_all_metrics,
            db
        )
        
        return {
            "status": "started",
            "message": "Metrics recalculation started in background"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting calculation: {str(e)}"
        )


@router.get("/data-quality-check")
def check_data_quality(db: Session = Depends(get_db)):
    """
    Run data quality checks on existing bookings.
    Returns validation report without modifying data.
    """
    try:
        from app.services.data_validator import BookingDataValidator
        
        # Extract bookings
        pipeline = ETLPipeline(db)
        df = pipeline.extract_from_database()
        
        # Validate
        validator = BookingDataValidator()
        report = validator.validate_dataframe(df)
        
        return report.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking data quality: {str(e)}"
        )


@router.get("/feature-summary")
def get_feature_summary(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get summary of engineered features from recent bookings.
    Shows what ML features are available.
    """
    try:
        from app.services.feature_engineering import FeatureEngineer
        
        # Extract recent bookings
        pipeline = ETLPipeline(db)
        df = pipeline.extract_from_database()
        
        if df.empty:
            return {"message": "No bookings found"}
        
        # Limit for performance
        df = df.head(limit)
        
        # Create features
        df_featured = FeatureEngineer.create_all_features(df, db)
        
        # Get summary
        summary = FeatureEngineer.get_feature_summary(df_featured)
        
        # Sample data
        sample = df_featured.head(5).to_dict(orient='records')
        
        return {
            "feature_summary": summary,
            "sample_records": sample
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating feature summary: {str(e)}"
        )