import pandas as pd
import numpy as np
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from fpdf import FPDF

def run_pipeline():
    print("Starting data pipeline...")
    input_file = r"C:\Users\Dell\Downloads\waste-dashboard\.next\dataset\Waste_Collection___Diversion_Report__daily_.csv"
    
    # Phase 1: Setup and Loading
    print("Phase 1: Loading data...")
    df = pd.read_csv(input_file)
    
    # Phase 2: EDA
    print("Phase 2: EDA...")
    eda_metrics = {
        "original_shape": df.shape,
        "columns": list(df.columns),
        "missing_values": df.isnull().sum().to_dict(),
        "duplicate_count": int(df.duplicated().sum()),
        "summary_stats": df.describe(include='all').to_dict()
    }
    
    # Phase 3: Data Cleaning
    print("Phase 3: Data Cleaning...")
    # Drop completely empty columns
    df = df.dropna(axis=1, how='all')
    # Drop columns with > 80% nulls
    threshold = 0.8 * len(df)
    df = df.dropna(axis=1, thresh=len(df) - threshold)
    
    # Drop administrative columns like Load ID
    cols_to_drop = [col for col in df.columns if 'id' in col.lower() or 'notes' in col.lower()]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        
    # Drop duplicates
    df = df.drop_duplicates()
    
    # Handle Load Weight which might be target. Ensure it's numeric
    if 'Load Weight' in df.columns:
        df['Load Weight'] = pd.to_numeric(df['Load Weight'], errors='coerce')
        df = df.dropna(subset=['Load Weight']) # Drop where target is null
    
    # Save cleaned data
    print("Saving cleaned data...")
    df.to_csv("cleaned_waste_data.csv", index=False)
    
    # Phase 4: Feature Engineering
    print("Phase 4: Feature Engineering...")
    if 'Report Date' in df.columns:
        df['Report Date'] = pd.to_datetime(df['Report Date'], errors='coerce')
        df = df.dropna(subset=['Report Date'])
        
        # Extract date features
        df['day_of_week'] = df['Report Date'].dt.dayofweek
        df['month'] = df['Report Date'].dt.month
        df['quarter'] = df['Report Date'].dt.quarter
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Sort by date for rolling features
        df = df.sort_values(by='Report Date')
        
        # Rolling averages (e.g. 7-day average for similar load types)
        # Using a simple rolling average for Load Weight over the past 7 records 
        # (Assuming rows are daily collections, but actually they are individual loads)
        # To make it meaningful, we can group by Route Type or Load Type, but for simplicity we'll just do a global rolling mean
        df['rolling_7_load_weight'] = df['Load Weight'].rolling(window=7, min_periods=1).mean()
        
        # Drop the original datetime if not needed by XGBoost, but we can keep it as float for now
        df['Report Date'] = df['Report Date'].astype('int64') // 10**9 # Unix timestamp
        
    if 'Load Time' in df.columns:
        df = df.drop(columns=['Load Time']) # Drop time for simplicity or could extract hour
        
    # Phase 5: XGBoost Prep
    print("Phase 5: Prep for XGBoost...")
    # Encode categorical variables
    categorical_cols = df.select_dtypes(include=['object']).columns
    encoders = {}
    
    for col in categorical_cols:
        le = LabelEncoder()
        # Handle unseen/null by converting to string
        df[col] = df[col].astype(str)
        df[col] = le.fit_transform(df[col])
        encoders[col] = list(le.classes_)
        
    # Impute missing values with median for numeric
    df = df.fillna(df.median())
    
    # Train/Val/Test split (70/15/15)
    train_df, temp_df = train_test_split(df, test_size=0.3, random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)
    
    print("Phase 6: Output Generation...")
    df.to_csv("processed_waste_data.csv", index=False)
    
    # Save metadata
    metadata = {
        "categorical_encodings": encoders,
        "features_list": list(df.columns),
        "target_variable": "Load Weight",
        "data_shape": df.shape,
        "splits": {
            "train": train_df.shape[0],
            "val": val_df.shape[0],
            "test": test_df.shape[0]
        }
    }
    with open("feature_metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    # PDF Report
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Data Quality Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.cell(200, 10, txt="1. Original Dataset Overview", ln=True)
    pdf.cell(200, 10, txt=f"Shape: {eda_metrics['original_shape']}", ln=True)
    pdf.cell(200, 10, txt=f"Duplicates Found: {eda_metrics['duplicate_count']}", ln=True)
    
    pdf.ln(5)
    pdf.cell(200, 10, txt="2. Missing Values (Top 5):", ln=True)
    sorted_missing = sorted(eda_metrics['missing_values'].items(), key=lambda item: item[1], reverse=True)[:5]
    for k, v in sorted_missing:
        pdf.cell(200, 10, txt=f"{k}: {v} missing", ln=True)
        
    pdf.ln(5)
    pdf.cell(200, 10, txt="3. Processed Dataset Details", ln=True)
    pdf.cell(200, 10, txt=f"Final Shape: {df.shape}", ln=True)
    pdf.cell(200, 10, txt=f"Train/Val/Test Split: {train_df.shape[0]} / {val_df.shape[0]} / {test_df.shape[0]}", ln=True)
    
    pdf.output("data_quality_report.pdf")
    print("Pipeline complete. All files generated.")

if __name__ == "__main__":
    run_pipeline()
