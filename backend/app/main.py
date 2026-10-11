import sys
sys.modules['transformers'] = None
import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.database import engine, Base
from backend.app.services.seed_service import seed_database_if_empty, SEED_STATUS
from backend.app.services.simulation import simulation_manager

from backend.app.api.routes_patients import router as patients_router
from backend.app.api.routes_alerts import router as alerts_router
from backend.app.api.routes_data import router as data_router
from backend.app.api.routes_models import router as models_router
from backend.app.api.routes_calibration import router as calibration_router
from backend.app.api.routes_evaluation import router as evaluation_router
from backend.app.api.routes_settings import router as settings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and seed demo cohort if needed
    Base.metadata.create_all(bind=engine)
    seed_database_if_empty()
    yield
    # Shutdown
    simulation_manager.pause()

app = FastAPI(
    title="SepsisWatch: ICU Early Warning System API",
    description="Clinical-grade ICU early sepsis alerting research & portfolio system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(patients_router)
app.include_router(alerts_router)
app.include_router(data_router)
app.include_router(models_router)
app.include_router(calibration_router)
app.include_router(evaluation_router)
app.include_router(settings_router)

# Simulation REST endpoints
class SpeedRequest(BaseModel):
    speed: float

@app.get("/api/simulation/status")
def get_simulation_status():
    return simulation_manager.get_overview_state()

@app.post("/api/simulation/start")
def start_simulation():
    simulation_manager.start()
    return {"status": "started", "is_running": simulation_manager.is_running}

@app.post("/api/simulation/pause")
def pause_simulation():
    simulation_manager.pause()
    return {"status": "paused", "is_running": simulation_manager.is_running}

@app.post("/api/simulation/reset")
def reset_simulation():
    simulation_manager.reset()
    return {"status": "reset", "is_running": False}

@app.post("/api/simulation/step")
def step_simulation():
    simulation_manager.step()
    return simulation_manager.get_overview_state()

@app.post("/api/simulation/speed")
def set_simulation_speed(req: SpeedRequest):
    simulation_manager.set_speed(req.speed)
    return {"status": "speed_set", "speed": simulation_manager.speed}

@app.get("/api/seed/status")
def get_seed_status():
    return SEED_STATUS

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "SepsisWatch"}

# WebSocket for real-time live bed grid and streaming replay
@app.websocket("/ws/simulation")
async def simulation_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    simulation_manager.add_listener(websocket)
    try:
        while True:
            # Poll or wait for messages from client (e.g. ping or commands)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                cmd = json.loads(data)
                action = cmd.get("action")
                if action == "start":
                    simulation_manager.start()
                elif action == "pause":
                    simulation_manager.pause()
                elif action == "reset":
                    simulation_manager.reset()
                elif action == "speed":
                    simulation_manager.set_speed(float(cmd.get("speed", 5.0)))
            except asyncio.TimeoutError:
                pass

            # Stream current state to client
            state = simulation_manager.get_overview_state()
            await websocket.send_text(json.dumps(state))
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        simulation_manager.remove_listener(websocket)
    except Exception:
        simulation_manager.remove_listener(websocket)
