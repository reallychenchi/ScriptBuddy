from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import os
from api.services.config_service import ConfigService
from api.services.script_service import ScriptService
from api.proxy.asr_proxy import asr_websocket_endpoint
from api.proxy.tts_proxy import tts_websocket_endpoint

# ... (omitted)

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... (omitted)

# --- WebSockets ---
@app.websocket("/api/ws/asr")
async def ws_asr(websocket: WebSocket):
    await asr_websocket_endpoint(websocket)

@app.websocket("/api/ws/tts")
async def ws_tts(websocket: WebSocket):
    await tts_websocket_endpoint(websocket)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Config API ---
@app.get("/api/config")
async def get_config():
    """下发给前端的配置 (仅 LLM)"""
    return ConfigService.get_public_config()

# --- Script API ---
@app.get("/api/script")
async def get_script(id: int = 1):
    script = ScriptService.get_script_by_id(id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script

# --- Admin API (Simple) ---
class ScriptLineModel(BaseModel):
    action: str
    story_id: int = 1
    id: Optional[int] = None
    role: Optional[str] = None
    content: Optional[str] = None
    duration: Optional[int] = 3000
    sort: Optional[int] = 0

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    # Load HTML directly
    with open(os.path.join(os.path.dirname(__file__), "templates/admin.html"), "r") as f:
        return f.read()

@app.post("/api/admin")
async def admin_action(data: ScriptLineModel):
    # TODO: Implement admin logic in ScriptService
    if data.action == "add":
        ScriptService.add_line(data)
    elif data.action == "update":
        ScriptService.update_line(data)
    elif data.action == "delete":
        if data.id:
            ScriptService.delete_line(data.id)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
