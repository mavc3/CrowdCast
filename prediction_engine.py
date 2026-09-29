import pickle
import os
import pandas as pd
import logging
from datetime import datetime, timedelta

class PredictionEngine:
    _instance = None
    _models_loaded = False
    
    crowd_model = None
    visitor_model = None
    label_encoders = None
    _prediction_cache = {} # Cache for performance optimization

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PredictionEngine, cls).__new__(cls)
            cls._instance._load_models()
        return cls._instance

    def _load_models(self):
        if PredictionEngine._models_loaded:
            return
            
        base_path = os.path.dirname(os.path.abspath(__file__))
        model_dir = os.path.join(base_path, 'models')
        
        try:
            with open(os.path.join(model_dir, 'crowd_classifier_model.pkl'), 'rb') as f:
                PredictionEngine.crowd_model = pickle.load(f)
            with open(os.path.join(model_dir, 'visitor_regressor_model.pkl'), 'rb') as f:
                PredictionEngine.visitor_model = pickle.load(f)
            with open(os.path.join(model_dir, 'label_encoders.pkl'), 'rb') as f:
                PredictionEngine.label_encoders = pickle.load(f)
            
            PredictionEngine._models_loaded = True
            logging.info("ML Models loaded successfully.")
        except Exception as e:
            logging.error(f"FATAL: Failed to load ML models: {e}")
            PredictionEngine._models_loaded = False

    def is_ready(self):
        return PredictionEngine._models_loaded

    def predict(self, service, stadium, timestamp=None):
        if not PredictionEngine._models_loaded:
            return 0, "Unknown"

        from datetime import datetime
        dt = timestamp if timestamp else datetime.now()
        
        # Performance Cache Logic
        cache_key = f"{service.id}_{dt.strftime('%Y%m%d%H')}"
        now_time = datetime.now()
        if cache_key in self._prediction_cache:
            cached_val, expiry = self._prediction_cache[cache_key]
            if now_time < expiry:
                return cached_val
        
        try:
            # 1. Feature Engineering (Categorical Mapping)
            raw_type = service.type.lower() if service.type else "restaurant"
            mapped_type = "cafe" if "cafe" in raw_type or "snack" in raw_type else \
                          "fast_food" if "truck" in raw_type or "fast" in raw_type else "restaurant"
            
            # Simple heuristics for binned/encoded features
            hour = dt.hour
            dow = dt.weekday()
            is_peak = True if (17 <= hour <= 21) else False
            is_lunch = True if (12 <= hour <= 14) else False
            is_dinner = True if (19 <= hour <= 21) else False
            is_weekend = True if dow >= 5 else False
            
            # Map Qatari Stadiums to Model's Recognized Labels (Saudi Stadiums)
            stadium_map = {
                'Lusail Stadium': 'King Abdullah Sports City',
                'Al Bayt Stadium': 'King Fahd International Stadium',
                'Education City Stadium': 'King Abdullah City Stadium',
                'Al Janoub Stadium': 'Prince Faisal bin Fahd Stadium',
                'Khalifa International Stadium': 'Prince Mohammed bin Fahd Stadium',
                'Ahmad bin Ali Stadium': 'King Fahd International Stadium'
            }
            mapped_stadium = stadium_map.get(stadium.name, 'King Abdullah Sports City')

            # 2. Real-Pulse Occupancy Detection
            from .models import Visit
            # Count users who checked in within the last 1 hour of the target timestamp
            lookback = dt - timedelta(hours=1)
            active_visits = Visit.query.filter(
                Visit.service_id == service.id,
                Visit.timestamp >= lookback,
                Visit.timestamp <= dt
            ).count()
            
            # Construct Base Feature Dictionary
            occupancy_rate = active_visits / service.capacity if service.capacity > 0 else 0.5
            
            reg_data = {
                'service_type': mapped_type,
                'latitude': 25.3 + (random.random() * 0.05),
                'longitude': 51.5 + (random.random() * 0.05),
                'nearest_stadium': mapped_stadium,
                'stadium_distance': 0.1, 
                'proximity_category': 'Very Close', 
                'service_capacity': service.capacity,
                'month': dt.month,
                'day': dt.day,
                'hour': hour,
                'day_of_week': dow,
                'is_weekend': is_weekend,
                'occupancy_rate': occupancy_rate,
                'is_lunch_time': is_lunch,
                'is_dinner_time': is_dinner,
                'is_peak_hour': is_peak,
                'proximity_score': 95.0, 
                'expected_crowd_percentage': occupancy_rate * 100,
                'capacity_category': 'Large' if service.capacity > 500 else 'Medium' if service.capacity > 200 else 'Small'
            }
            
            reg_df = pd.DataFrame([reg_data])
            # Reorder to match model's expected order
            reg_df = reg_df[PredictionEngine.visitor_model.feature_names_in_]
            
            # Apply encoders
            for col, encoder in PredictionEngine.label_encoders.items():
                if col in reg_df.columns:
                    reg_df[col] = encoder.transform(reg_df[col].astype(str))
            
            # Predict Visitors
            visitors = int(PredictionEngine.visitor_model.predict(reg_df)[0])
            
            # 3. Construct Classifier Dictionary (expects 18 features)
            cls_data = reg_data.copy()
            cls_data.pop('occupancy_rate', None)
            cls_data.pop('expected_crowd_percentage', None)
            cls_data['expected_visitors'] = visitors
            
            cls_df = pd.DataFrame([cls_data])
            # Reorder to match model's expected order
            cls_df = cls_df[PredictionEngine.crowd_model.feature_names_in_]
            
            for col, encoder in PredictionEngine.label_encoders.items():
                if col in cls_df.columns:
                    cls_df[col] = encoder.transform(cls_df[col].astype(str))
            
            level_idx = int(PredictionEngine.crowd_model.predict(cls_df)[0])
            levels = {0: 'Low', 1: 'Medium', 2: 'High', 3: 'Critical'}
            level = levels.get(level_idx, 'Medium')
            
            result = (max(0, visitors), level)
            
            # Store in cache (expire in 30 seconds)
            self._prediction_cache[cache_key] = (result, now_time + timedelta(seconds=30))
            
            return result
            
        except Exception as e:
            logging.error(f"Inference Error: {e}")
            return 0, "Error"

import random # Required for synthetic jitter
