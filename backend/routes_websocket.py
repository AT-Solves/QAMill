"""
WebSocket routes - Real-time analysis updates and team activity
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from websocket_manager import manager
from database import SessionLocal
from services.auth_service import AuthService
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_ws_token(token: str, db: Session = Depends(get_db)) -> str:
    """Verify WebSocket token and return user_id"""
    auth_service = AuthService(db)
    payload = auth_service.verify_token(token)

    if not payload:
        raise ValueError("Invalid token")

    return payload.get("sub")


@router.websocket("/analysis/{analysis_id}")
async def analysis_websocket(
    websocket: WebSocket,
    analysis_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """WebSocket connection for real-time analysis updates"""
    try:
        # Verify token
        user_id = verify_ws_token(token, db)
    except ValueError:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    connection_id = str(uuid.uuid4())

    try:
        # Accept connection
        await manager.connect(websocket, user_id, connection_id)

        # Subscribe to analysis
        await manager.subscribe_to_analysis(analysis_id, user_id)

        # Send connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "analysis_id": analysis_id,
                "connection_id": connection_id,
                "message": "Connected to analysis updates",
            }
        )

        # Keep connection open and listen for messages
        while True:
            data = await websocket.receive_text()
            # Echo received message back
            await websocket.send_json(
                {
                    "type": "ack",
                    "connection_id": connection_id,
                }
            )

    except WebSocketDisconnect:
        manager.disconnect(user_id, connection_id)
        await manager.unsubscribe_from_analysis(analysis_id, user_id)
        logger.info(f"User {user_id} disconnected from analysis {analysis_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(user_id, connection_id)


@router.websocket("/project/{project_id}")
async def project_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """WebSocket connection for real-time project updates"""
    try:
        # Verify token
        user_id = verify_ws_token(token, db)
    except ValueError:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    connection_id = str(uuid.uuid4())

    try:
        # Accept connection
        await manager.connect(websocket, user_id, connection_id)

        # Subscribe to project
        await manager.subscribe_to_project(project_id, user_id)

        # Send connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "project_id": project_id,
                "connection_id": connection_id,
                "message": "Connected to project updates",
            }
        )

        # Keep connection open
        while True:
            data = await websocket.receive_text()
            # Echo received message back
            await websocket.send_json(
                {
                    "type": "ack",
                    "connection_id": connection_id,
                }
            )

    except WebSocketDisconnect:
        manager.disconnect(user_id, connection_id)
        await manager.unsubscribe_from_project(project_id, user_id)
        logger.info(f"User {user_id} disconnected from project {project_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(user_id, connection_id)


# HTTP endpoints for broadcasting updates (called by analysis service)
@router.post("/broadcast/analysis/{analysis_id}")
async def broadcast_analysis_update(
    analysis_id: str,
    event_type: str = Query(...),
    data: dict = {},
):
    """Broadcast analysis update to all subscribers"""
    await manager.broadcast_analysis_update(analysis_id, event_type, data)
    return {"status": "broadcasted", "subscribers": manager.get_analysis_subscriber_count(analysis_id)}


@router.post("/broadcast/project/{project_id}")
async def broadcast_project_update(
    project_id: str,
    event_type: str = Query(...),
    data: dict = {},
):
    """Broadcast project update to all subscribers"""
    await manager.broadcast_project_update(project_id, event_type, data)
    return {"status": "broadcasted", "subscribers": manager.get_project_subscriber_count(project_id)}


# Status endpoints
@router.get("/status")
async def ws_status():
    """Get WebSocket status"""
    return {
        "online_users": manager.get_online_users_count(),
        "active_analyses": len(manager.analysis_subscribers),
        "active_projects": len(manager.project_subscribers),
    }
