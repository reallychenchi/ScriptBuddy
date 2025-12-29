import pytest
from httpx import AsyncClient
from api.main import app
from api.db import execute_query

# Note: These tests require the database to be accessible.

@pytest.mark.asyncio
async def test_get_config():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "llm" in data
    # ASR/TTS should be hidden
    assert "asr" not in data
    assert "tts" not in data

@pytest.mark.asyncio
async def test_get_script():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/script?id=1")
    assert response.status_code == 200
    data = response.json()
    assert "meta" in data
    assert "lines" in data
    assert len(data["lines"]) > 0

@pytest.mark.asyncio
async def test_admin_add_delete():
    # 1. Add
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "action": "add",
            "role": "甲",
            "content": "Test Line",
            "sort": 999
        }
        await ac.post("/api/admin", json=payload)

    # 2. Verify
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/script?id=1")
        data = response.json()
        lines = data["lines"]
        test_line = next((l for l in lines if l["content"] == "Test Line"), None)
        assert test_line is not None

    # 3. Delete
    if test_line:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            await ac.post("/api/admin", json={"action": "delete", "id": test_line["id"]})
