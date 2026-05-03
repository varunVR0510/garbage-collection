from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.dashboard import router as dashboard_router
from routes.predictions import router as predictions_router
from routes.fleet import router as fleet_router
from routes.routing import router as routing_router
from routes.alerts import router as alerts_router
from routes.analytics import router as analytics_router

app = FastAPI(title="Austin SmartWaste Backend API")

# Allow CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(fleet_router, prefix="/api/fleet")
app.include_router(routing_router, prefix="/api/routes")
app.include_router(alerts_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to Austin SmartWaste Backend API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
