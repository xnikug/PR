from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import asyncio
import httpx
import os
import random
from contextlib import asynccontextmanager

ROLE = os.getenv("ROLE", "follower")
PORT = int(os.getenv("PORT", "8000"))
WRITE_QUORUM = int(os.getenv("WRITE_QUORUM"))
MIN_DELAY = int(os.getenv("MIN_DELAY", "0"))
MAX_DELAY = int(os.getenv("MAX_DELAY", "1000"))

FOLLOWER_URLS = os.getenv("FOLLOWER_URLS", "").split(",") if os.getenv("FOLLOWER_URLS") else []

store: Dict[str, str] = {}
store_lock = asyncio.Lock()


class KeyValue(BaseModel):
    key: str
    value: str


class WriteResponse(BaseModel):
    success: bool
    message: str
    replicated_count: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {ROLE} on port {PORT}")
    if ROLE == "leader":
        print(f"Write quorum: {WRITE_QUORUM}")
        print(f"Followers: {FOLLOWER_URLS}")
        print(f"Delay range: [{MIN_DELAY}ms, {MAX_DELAY}ms]")
    yield
    # Shutdown
    print(f"Shutting down {ROLE}")


app = FastAPI(lifespan=lifespan)


async def replicate_to_follower(follower_url: str, key: str, value: str) -> bool:
    try:
        # Simulate network lag
        delay_ms = random.randint(MIN_DELAY, MAX_DELAY)
        await asyncio.sleep(delay_ms / 1000.0)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{follower_url}/replicate",
                json={"key": key, "value": value}
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Error replicating to {follower_url}: {e}")
        return False


async def replicate_to_followers(key: str, value: str) -> int:
    tasks = [asyncio.create_task(replicate_to_follower(url, key, value))
             for url in FOLLOWER_URLS]

    success_count = 0

    for completed in asyncio.as_completed(tasks):
        result = await completed
        
        if result:
            success_count += 1
            
        # QUORUM REACHED stop waiting
        if success_count >= WRITE_QUORUM:
            # FORGOT BREAK HERE 😭
            break

    return success_count



@app.post("/write", response_model=WriteResponse)
async def write(kv: KeyValue):
    if ROLE != "leader":
        raise HTTPException(status_code=403, detail="Only leader accepts writes")
    
    # Write to leader's store
    async with store_lock:
        store[kv.key] = kv.value
    
    replicated_count = await replicate_to_followers(kv.key, kv.value)
    
    # Check if write quorum is met
    if replicated_count >= WRITE_QUORUM:
        return WriteResponse(
            success=True,
            message=f"Write successful, replicated to {replicated_count} followers",
            replicated_count=replicated_count
        )
    else:
        # Write is on leader but quorum not met
        return WriteResponse(
            success=False,
            message=f"Write quorum not met. Replicated to {replicated_count}/{WRITE_QUORUM} required followers",
            replicated_count=replicated_count
        )


@app.post("/replicate")
async def replicate(kv: KeyValue):
    if ROLE == "leader":
        raise HTTPException(status_code=403, detail="Leader doesn't accept replication requests")
    
    async with store_lock:
        store[kv.key] = kv.value
    
    return {"status": "ok"}


@app.get("/read/{key}")
async def read(key: str):
    async with store_lock:
        if key in store:
            return {"key": key, "value": store[key]}
        else:
            raise HTTPException(status_code=404, detail="Key not found")


@app.get("/dump")
async def dump():
    async with store_lock:
        return {"data": store, "role": ROLE}


@app.get("/health")
async def health():
    return {"status": "healthy", "role": ROLE}