"""
WebSocket Connection Manager
Manages real-time WebSocket connections for notifications
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        logger.info("ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            user_id: Unique user identifier
        """
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "message": "WebSocket connected successfully",
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)
    
    def disconnect(self, user_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            user_id: User identifier to disconnect
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """
        Send a message to a specific user.
        
        Args:
            message: Message dictionary to send
            user_id: Target user identifier
        """
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                logger.debug(f"Sent message to user {user_id}: {message.get('type')}")
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast(self, message: dict, exclude: Optional[List[str]] = None):
        """
        Broadcast a message to all connected users.
        
        Args:
            message: Message dictionary to broadcast
            exclude: Optional list of user IDs to exclude
        """
        exclude = exclude or []
        disconnected = []
        
        for user_id, connection in self.active_connections.items():
            if user_id in exclude:
                continue
            
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {user_id}: {e}")
                disconnected.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected:
            self.disconnect(user_id)
        
        logger.info(f"Broadcast message to {len(self.active_connections) - len(exclude)} users")
    
    async def send_meta_shift_notification(self, brawler: str, change: str, delta: str):
        """Send meta shift notification to all users"""
        await self.broadcast({
            "type": "meta_shift",
            "brawler": brawler,
            "change": change,
            "delta": delta,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_event_rotation_notification(self, new_events: List[dict]):
        """Send event rotation notification to all users"""
        await self.broadcast({
            "type": "event_rotation",
            "new_events": new_events,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_milestone_notification(self, user_id: str, achievement: str, brawler: str):
        """Send player milestone notification"""
        await self.send_personal_message({
            "type": "milestone",
            "achievement": achievement,
            "brawler": brawler,
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def is_connected(self, user_id: str) -> bool:
        """Check if a user is connected"""
        return user_id in self.active_connections
