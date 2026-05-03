import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os
import hashlib

from ml.demographics import features_for as demographic_features_for
from ml.route_geometry import district_for_route as geo_district_for_route


def generate_district_features(df):
    df['Report Date'] = pd.to_datetime(df['Report Date'], errors='coerce')
    df = df.dropna(subset=['Report Date', 'Route Number', 'Load Weight'])

    districts = [f"District {i}" for i in range(1, 11)]

    def get_district(route):
        # Prefer real geography (route polygons in austin_routes_2015.xlsx).
        # Fall back to deterministic hash for routes not in the geometry file.
        d = geo_district_for_route(route)
        if d is not None:
            return d
        val = int(hashlib.md5(str(route).encode()).hexdigest(), 16)
        return districts[val % 10]

    df['district'] = df['Route Number'].apply(get_district)

    df['day_of_week'] = df['Report Date'].dt.dayofweek
    df['month'] = df['Report Date'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

    district_mapping = {d: i for i, d in enumerate(districts)}
    df['district_encoded'] = df['district'].map(district_mapping)

    df['Load Weight'] = pd.to_numeric(df['Load Weight'], errors='coerce')
    df = df.dropna(subset=['Load Weight'])

    df = df.sort_values(by=['district_encoded', 'Report Date'])
    df['rolling_7_load_weight'] = df.groupby('district_encoded')['Load Weight'].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )

    df = df.dropna(subset=['rolling_7_load_weight'])

    demo_cols = ['population', 'households', 'area_sqkm', 'population_density',
                 'commercial_index', 'income_level_encoded']
    demo_df = pd.DataFrame([
        {'district': name, **demographic_features_for(name)} for name in districts
    ])
    df = df.merge(demo_df, on='district', how='left')

    max_capacities = df.groupby('district')['Load Weight'].max().to_dict()

    return df, district_mapping, max_capacities, demo_cols


def _resolve_csv_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "..", "..", "cleaned_waste_data.csv"),
        os.path.join(base_dir, "..", "cleaned_waste_data.csv"),
        os.path.abspath(os.path.join(os.getcwd(), "cleaned_waste_data.csv")),
        os.path.abspath(os.path.join(os.getcwd(), "..", "cleaned_waste_data.csv")),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None


def train_model() -> dict:
    """Train XGBoost on the Austin dataset. Returns dict with metrics."""
    input_file = _resolve_csv_path()
    if not input_file:
        raise FileNotFoundError("cleaned_waste_data.csv not found in expected locations")

    df = pd.read_csv(input_file, usecols=['Report Date', 'Route Number', 'Load Weight'])
    df, district_mapping, max_capacities, demo_cols = generate_district_features(df)

    features = ['district_encoded', 'day_of_week', 'month', 'is_weekend', 'rolling_7_load_weight'] + demo_cols
    target = 'Load Weight'

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = xgb.XGBRegressor(
        n_estimators=200,
        learning_rate=0.08,
        max_depth=6,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = float(r2_score(y_test, y_pred))
    mae = float(mean_absolute_error(y_test, y_pred))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "model.joblib")
    joblib.dump({
        'model': model,
        'district_mapping': district_mapping,
        'max_capacities': max_capacities,
        'feature_order': features,
    }, model_path)

    return {
        "r2": r2,
        "mae": mae,
        "n_samples": int(len(df)),
        "model_path": model_path,
    }


if __name__ == "__main__":
    result = train_model()
    print(f"R² Score: {result['r2']:.4f}  MAE: {result['mae']:.2f}  n={result['n_samples']}")
    print(f"Model saved to {result['model_path']}")
