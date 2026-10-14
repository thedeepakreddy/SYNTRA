"""Event logging and real-time WebSocket streaming endpoints."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from syntra.core.events import get_event_bus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["events"])


@router.get("/api/events")
async def get_events(session_id: str | None = None, limit: int = 100) -> list[dict]:
    """Retrieve recent event history."""
    bus = get_event_bus()
    events = bus.get_history(session_id=session_id, limit=limit)
    return [e.to_dict() for e in events]


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    """Stream real-time SYNTRA events over WebSocket."""
    await websocket.accept()
    bus = get_event_bus()
    queue = bus.create_event_queue()

    try:
        while True:
            event = await queue.get()
            data = event.to_dict()
            await websocket.send_text(json.dumps(data))
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from event stream.")
    except Exception as exc:
        logger.warning("Error in WebSocket event streaming: %s", exc)
    finally:
        bus.remove_event_queue(queue)
