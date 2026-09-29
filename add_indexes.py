from app import create_app, db
from sqlalchemy import text

def add_indexes():
    app = create_app()
    with app.app_context():
        print("INITIATING DATABASE OPTIMIZATION...")
        
        # Service indexing for stadium-scoped searches
        try:
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_services_stadium_id ON services(stadium_id)"))
            print("SUCCESS: idx_services_stadium_id established.")
        except Exception as e:
            print(f"SKIPPED: idx_services_stadium_id (may already exist): {e}")

        # PredictionResults indexing for sub-second retrieval
        try:
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_prediction_results_service_stadium ON prediction_results(service_id, date, hour)"))
            print("SUCCESS: idx_prediction_results_service_stadium established.")
        except Exception as e:
            print(f"SKIPPED: idx_prediction_results_service_stadium (may already exist): {e}")

        db.session.commit()
        print("DATABASE OPTIMIZATION COMPLETE.")

if __name__ == "__main__":
    add_indexes()
