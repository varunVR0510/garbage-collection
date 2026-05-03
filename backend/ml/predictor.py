import os
import joblib
import pandas as pd
from datetime import datetime

class XGBoostPredictor:
    def __init__(self, model_path="model.joblib"):
        if not os.path.exists(model_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_dir, model_path)
            
        if os.path.exists(model_path):
            data = joblib.load(model_path)
            self.model = data['model']
            self.district_mapping = data['district_mapping']
            self.max_capacities = data['max_capacities']
        else:
            print(f"Warning: Model not found at {model_path}. Predictions will fail.")
            self.model = None
            self.district_mapping = {}
            self.max_capacities = {}

    def predict_district_waste(self, district_name, date, rolling_7_load_weight):
        if not self.model:
            return 0.0

        # Always convert to pandas timestamp to ensure consistency
        date = pd.to_datetime(date)

        day_of_week = date.dayofweek
        month = date.month
        is_weekend = 1 if day_of_week in [5, 6] else 0

        district_encoded = self.district_mapping.get(district_name, 0)

        features = pd.DataFrame([{
            'district_encoded': district_encoded,
            'day_of_week': day_of_week,
            'month': month,
            'is_weekend': is_weekend,
            'rolling_7_load_weight': rolling_7_load_weight
        }])

        prediction = self.model.predict(features)[0]
        # Return in tons (assuming original Load Weight was lbs)
        return float(prediction) * 0.0005

    def get_max_capacity_tons(self, district_name):
        return self.max_capacities.get(district_name, 200000) * 0.0005

predictor = XGBoostPredictor()
