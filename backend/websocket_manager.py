"""
WebSocket Manager - Real-time updates for mutation analysis
Handles live progress streaming, test results, and team activity
"""
from typing import Set, Dict, List
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        # Active connections: {user_id: {connection_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Analysis subscribers: {analysis_id: {user_id1, user_id2, ...}}
        self.analysis_subscribers: Dict[str, Set[str]] = {}
        # Project subscribers: {project_id: {user_id1, user_id2, ...}}
        self.project_subscribers: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        """Register a new WebSocket connection"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}

        self.active_connections[user_id][connection_id] = websocket
        logger.info(f"User {user_id} connected (ID: {connection_id})")

    def disconnect(self, user_id: str, connection_id: str):
        """Unregister a WebSocket connection"""
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]

            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        logger.info(f"User {user_id} disconnected (ID: {connection_id})")

    async def subscribe_to_analysis(self, analysis_id: str, user_id: str):
        """Subscribe user to analysis updates"""
        if analysis_id not in self.analysis_subscribers:
            self.analysis_subscribers[analysis_id] = set()

        self.analysis_subscribers[analysis_id].add(user_id)
        logger.info(f"User {user_id} subscribed to analysis {analysis_id}")

    async def unsubscribe_from_analysis(self, analysis_id: str, user_id: str):
        """Unsubscribe user from analysis updates"""
        if analysis_id in self.analysis_subscribers:
            self.analysis_subscribers[analysis_id].discard(user_id)

            if not self.analysis_subscribers[analysis_id]:
                del self.analysis_subscribers[analysis_id]

        logger.info(f"User {user_id} unsubscribed from analysis {analysis_id}")

    async def subscribe_to_project(self, project_id: str, user_id: str):
        """Subscribe user to project updates"""
        if project_id not in self.project_subscribers:
            self.project_subscribers[project_id] = set()

        self.project_subscribers[project_id].add(user_id)
        logger.info(f"User {user_id} subscribed to project {project_id}")

    async def unsubscribe_from_project(self, project_id: str, user_id: str):
        """Unsubscribe user from project updates"""
        if project_id in self.project_subscribers:
            self.project_subscribers[project_id].discard(user_id)

            if not self.project_subscribers[project_id]:
                del self.project_subscribers[project_id]

    async def broadcast_analysis_update(
        self,
        analysis_id: str,
        event_type: str,
        data: dict,
    ):
        """Broadcast analysis update to all subscribers"""
        if analysis_id not in self.analysis_subscribers:
            return

        message = {
            "type": "analysis_update",
            "event": event_type,
            "analysis_id": analysis_id,
            "data": data,
        }

        for user_id in self.analysis_subscribers[analysis_id]:
            await self.send_to_user(user_id, message)

    async def broadcast_project_update(
        self,
        project_id: str,
        event_type: str,
        data: dict,
    ):
        """Broadcast project update to all subscribers"""
        if project_id not in self.project_subscribers:
            return

        message = {
            "type": "project_update",
            "event": event_type,
            "project_id": project_id,
            "data": data,
        }

        for user_id in self.project_subscribers[project_id]:
            await self.send_to_user(user_id, message)

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a user"""
        if user_id not in self.active_connections:
            return

        message_str = json.dumps(message)
        disconnected = []

        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending to {user_id}: {e}")
                disconnected.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(user_id, connection_id)

    async def broadcast_activity(
        self,
        project_id: str,
        user_id: str,
        activity_type: str,
        details: dict,
    ):
        """Broadcast team activity to project subscribers"""
        message = {
            "type": "activity",
            "project_id": project_id,
            "user_id": user_id,
            "activity_type": activity_type,
            "details": details,
        }

        if project_id in self.project_subscribers:
            for subscriber_id in self.project_subscribers[project_id]:
                await self.send_to_user(subscriber_id, message)

    def get_online_users_count(self) -> int:
        """Get count of online users"""
        return len(self.active_connections)

    def get_analysis_subscriber_count(self, analysis_id: str) -> int:
        """Get count of subscribers for an analysis"""
        return len(self.analysis_subscribers.get(analysis_id, set()))

    def get_project_subscriber_count(self, project_id: str) -> int:
        """Get count of subscribers for a project"""
        return len(self.project_subscribers.get(project_id, set()))


# Global connection manager
manager = ConnectionManager()
