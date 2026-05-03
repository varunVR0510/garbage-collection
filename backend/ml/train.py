import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import os
import json
import hashlib

def generate_district_features(df):
    print("Mapping Austin dataset to 10 Geographic Districts...")
    
    df['Report Date'] = pd.to_datetime(df['Report Date'], errors='coerce')
    df = df.dropna(subset=['Report Date', 'Route Number', 'Load Weight'])
    
    # We define 10 Service Districts for Austin
    districts = [f"District {i}" for i in range(1, 11)]
    
    # Deterministically assign Route Numbers to a District
    def get_district(route):
        val = int(hashlib.md5(str(route).encode()).hexdigest(), 16)
        return districts[val % 10]
        
    df['district'] = df['Route Number'].apply(get_district)
    
    df['day_of_week'] = df['Report Date'].dt.dayofweek
    df['month'] = df['Report Date'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Encode District
    district_mapping = {d: i for i, d in enumerate(districts)}
    df['district_encoded'] = df['district'].map(district_mapping)
    
    df['Load Weight'] = pd.to_numeric(df['Load Weight'], errors='coerce')
    df = df.dropna(subset=['Load Weight'])
    
    # Calculate historical rolling average
    df = df.sort_values(by=['district_encoded', 'Report Date'])
    df['rolling_7_load_weight'] = df.groupby('district_encoded')['Load Weight'].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )
    
    # Drop rows without rolling avg
    df = df.dropna(subset=['rolling_7_load_weight'])
    
    # Calculate max capacity per district directly from data (no synthetic baseline)
    max_capacities = df.groupby('district')['Load Weight'].max().to_dict()
    
    return df, district_mapping, max_capacities

def train_model():
    input_file = r"..\..\cleaned_waste_data.csv"
    if not os.path.exists(input_file):
        print(f"Error: Could not find {input_file}")
        return

    print("Loading raw Austin dataset...")
    df = pd.read_csv(input_file, usecols=['Report Date', 'Route Number', 'Load Weight'])
    
    df, district_mapping, max_capacities = generate_district_features(df)
    
    features = [
        'district_encoded', 'day_of_week', 'month', 'is_weekend', 'rolling_7_load_weight'
    ]
    target = 'Load Weight'
    
    X = df[features]
    y = df[target]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training XGBoost Regressor on Real Austin Dataset...")
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    print("Evaluating model on real data...")
    y_pred = model.predict(X_test)
    
    r2 = r2_score(y_test, y_pred)
    print(f"R² Score: {r2:.4f}")
    
    model_path = "model.joblib"
    joblib.dump({
        'model': model, 
        'district_mapping': district_mapping,
        'max_capacities': max_capacities
    }, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_model()
