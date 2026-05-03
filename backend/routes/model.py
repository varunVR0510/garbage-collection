from fastapi import APIRouter, HTTPException
import db
from ml.predictor import predictor
from ml.train import train_model

router = APIRouter()


LBS_TO_TONS = 0.0005


def _label_from_mae_tons(mae_tons: float) -> str:
    if mae_tons <= 1.0:
        return "Strong"
    if mae_tons <= 2.5:
        return "Moderate"
    if mae_tons <= 5.0:
        return "Weak"
    return "Poor"


@router.get("/status")
def model_status():
    meta = db.latest_model_meta()
    if not meta:
        return {
            "r2": None,
            "mae_lbs": None,
            "mae_tons": None,
            "n_samples": None,
            "trained_at": None,
            "accuracy_label": "Untrained",
        }
    mae_lbs = float(meta["mae"]) if meta["mae"] is not None else 0.0
    mae_tons = mae_lbs * LBS_TO_TONS
    return {
        "r2": round(float(meta["r2_score"]), 3),
        "mae_lbs": round(mae_lbs, 1),
        "mae_tons": round(mae_tons, 2),
        "n_samples": meta["n_samples"],
        "trained_at": meta["trained_at"],
        "accuracy_label": _label_from_mae_tons(mae_tons),
    }


@router.post("/retrain")
def retrain():
    try:
        result = train_model()
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {e}")

    db.log_model_meta(result["r2"], result["mae"], result["n_samples"])
    predictor.reload()

    mae_tons = result["mae"] * LBS_TO_TONS
    return {
        "ok": True,
        "r2": round(result["r2"], 3),
        "mae_lbs": round(result["mae"], 1),
        "mae_tons": round(mae_tons, 2),
        "n_samples": result["n_samples"],
        "accuracy_label": _label_from_mae_tons(mae_tons),
    }
