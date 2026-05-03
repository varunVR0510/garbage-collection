import os
import joblib
import pandas as pd
from datetime import datetime
from ml.demographics import features_for as demographic_features_for

class XGBoostPredictor:
    def __init__(self, model_path="model.joblib"):
        self._default_path = model_path
        self.model = None
        self.district_mapping = {}
        self.max_capacities = {}
        self.reload()

    def reload(self, model_path: str = None):
        path = model_path or self._default_path
        if not os.path.exists(path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, os.path.basename(path))

        if os.path.exists(path):
            data = joblib.load(path)
            self.model = data['model']
            self.district_mapping = data['district_mapping']
            self.max_capacities = data['max_capacities']
            self.feature_order = data.get('feature_order')
        else:
            print(f"Warning: Model not found at {path}. Predictions will fail.")
            self.model = None
            self.district_mapping = {}
            self.max_capacities = {}
            self.feature_order = None

    def predict_district_waste(self, district_name, date, rolling_7_load_weight):
        if not self.model:
            return 0.0

        date = pd.to_datetime(date)
        day_of_week = date.dayofweek
        month = date.month
        is_weekend = 1 if day_of_week in [5, 6] else 0

        district_encoded = self.district_mapping.get(district_name, 0)
        demo = demographic_features_for(district_name)

        row = {
            'district_encoded': district_encoded,
            'day_of_week': day_of_week,
            'month': month,
            'is_weekend': is_weekend,
            'rolling_7_load_weight': rolling_7_load_weight,
            **demo,
        }

        if self.feature_order:
            features = pd.DataFrame([{k: row.get(k, 0.0) for k in self.feature_order}])
        else:
            features = pd.DataFrame([row])

        prediction = self.model.predict(features)[0]
        return float(prediction) * 0.0005

    def get_max_capacity_tons(self, district_name):
        return self.max_capacities.get(district_name, 200000) * 0.0005

predictor = XGBoostPredictor()
