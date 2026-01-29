"""
WebSocket Manager for BrawlGPT.
Handles real-time notifications and live updates.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Callable, Coroutine

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications that can be sent."""
    META_UPDATE = "meta_update"
    GOAL_PROGRESS = "goal_progress"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    CHALLENGE_AVAILABLE = "challenge_available"
    FRIEND_ACTIVITY = "friend_activity"
    EVENT_ROTATION = "event_rotation"
    SYSTEM_MESSAGE = "system_message"
    ERROR = "error"


@dataclass
class Notification:
    """Notification message structure."""
    type: NotificationType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_json(self) -> str:
        """Convert notification to JSON string."""
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        })


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    player_tag: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    subscriptions: set[str] = field(default_factory=set)


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.

    Usage:
        manager = WebSocketManager()

        # In WebSocket endpoint
        @app.websocket("/ws/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: str):
            await manager.connect(websocket, user_id)
            try:
                while True:
                    data = await websocket.receive_text()
                    await manager.handle_message(user_id, data)
            except WebSocketDisconnect:
                manager.disconnect(user_id)

        # Send notification
        await manager.send_notification(
            user_id,
            NotificationType.GOAL_PROGRESS,
            {"goal": "50k", "progress": 85}
        )

        # Broadcast to all
        await manager.broadcast(
            NotificationType.META_UPDATE,
            {"message": "New meta analysis available"}
        )
    """

    def __init__(self):
        # Active connections: user_id -> ConnectionInfo
        self._connections: dict[str, ConnectionInfo] = {}

        # Subscription groups: topic -> set of user_ids
        self._subscriptions: dict[str, set[str]] = {}

        # Message handlers: message_type -> handler function
        self._handlers: dict[str, Callable[[str, dict], Coroutine]] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

    @property
    def active_connections(self) -> int:
        """Get number of active connections."""
        return len(self._connections)

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        player_tag: Optional[str] = None
    ) -> None:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: User identifier
            player_tag: Optional player tag for personalized notifications
        """
        await websocket.accept()

        async with self._lock:
            # Close existing connection if any
            if user_id in self._connections:
                old_conn = self._connections[user_id]
                try:
                    await old_conn.websocket.close()
                except Exception:
                    pass

            self._connections[user_id] = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                player_tag=player_tag,
            )

        logger.info(f"WebSocket connected: user_id={user_id}, player_tag={player_tag}")

        # Send welcome message
        await self.send_notification(
            user_id,
            NotificationType.SYSTEM_MESSAGE,
            {"message": "Connected to BrawlGPT real-time notifications"}
        )

    def disconnect(self, user_id: str) -> None:
        """
        Handle WebSocket disconnection.

        Args:
            user_id: User identifier
        """
        if user_id in self._connections:
            conn = self._connections.pop(user_id)

            # Remove from all subscriptions
            for topic, subscribers in self._subscriptions.items():
                subscribers.discard(user_id)

            logger.info(f"WebSocket disconnected: user_id={user_id}")

    async def send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        data: dict[str, Any]
    ) -> bool:
        """
        Send a notification to a specific user.

        Args:
            user_id: Target user identifier
            notification_type: Type of notification
            data: Notification payload

        Returns:
            True if sent successfully, False otherwise
        """
        conn = self._connections.get(user_id)
        if not conn:
            return False

        try:
            notification = Notification(type=notification_type, data=data)
            await conn.websocket.send_text(notification.to_json())
            logger.debug(f"Sent notification to {user_id}: {notification_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to send notification to {user_id}: {e}")
            self.disconnect(user_id)
            return False

    async def broadcast(
        self,
        notification_type: NotificationType,
        data: dict[str, Any],
        exclude: Optional[set[str]] = None
    ) -> int:
        """
        Broadcast a notification to all connected users.

        Args:
            notification_type: Type of notification
            data: Notification payload
            exclude: Optional set of user_ids to exclude

        Returns:
            Number of users notified
        """
        exclude = exclude or set()
        notification = Notification(type=notification_type, data=data)
        message = notification.to_json()

        sent_count = 0
        failed_connections = []

        for user_id, conn in list(self._connections.items()):
            if user_id in exclude:
                continue

            try:
                if conn.websocket.client_state == WebSocketState.CONNECTED:
                    await conn.websocket.send_text(message)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Broadcast failed for {user_id}: {e}")
                failed_connections.append(user_id)

        # Clean up failed connections
        for user_id in failed_connections:
            self.disconnect(user_id)

        logger.info(
            f"Broadcast {notification_type.value} to {sent_count} users "
            f"({len(failed_connections)} failed)"
        )
        return sent_count

    async def broadcast_to_topic(
        self,
        topic: str,
        notification_type: NotificationType,
        data: dict[str, Any]
    ) -> int:
        """
        Broadcast to users subscribed to a specific topic.

        Args:
            topic: Topic name
            notification_type: Type of notification
            data: Notification payload

        Returns:
            Number of users notified
        """
        subscribers = self._subscriptions.get(topic, set())
        if not subscribers:
            return 0

        sent_count = 0
        for user_id in subscribers:
            if await self.send_notification(user_id, notification_type, data):
                sent_count += 1

        return sent_count

    def subscribe(self, user_id: str, topic: str) -> bool:
        """
        Subscribe a user to a topic.

        Args:
            user_id: User identifier
            topic: Topic to subscribe to

        Returns:
            True if subscribed successfully
        """
        if user_id not in self._connections:
            return False

        if topic not in self._subscriptions:
            self._subscriptions[topic] = set()

        self._subscriptions[topic].add(user_id)
        self._connections[user_id].subscriptions.add(topic)

        logger.debug(f"User {user_id} subscribed to {topic}")
        return True

    def unsubscribe(self, user_id: str, topic: str) -> bool:
        """
        Unsubscribe a user from a topic.

        Args:
            user_id: User identifier
            topic: Topic to unsubscribe from

        Returns:
            True if unsubscribed successfully
        """
        if topic in self._subscriptions:
            self._subscriptions[topic].discard(user_id)

        if user_id in self._connections:
            self._connections[user_id].subscriptions.discard(topic)

        return True

    async def handle_message(self, user_id: str, message: str) -> None:
        """
        Handle an incoming message from a client.

        Args:
            user_id: User who sent the message
            message: Raw message string
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "ping":
                await self.send_notification(
                    user_id,
                    NotificationType.SYSTEM_MESSAGE,
                    {"type": "pong"}
                )

            elif message_type == "subscribe":
                topic = data.get("topic")
                if topic:
                    self.subscribe(user_id, topic)

            elif message_type == "unsubscribe":
                topic = data.get("topic")
                if topic:
                    self.unsubscribe(user_id, topic)

            elif message_type in self._handlers:
                handler = self._handlers[message_type]
                await handler(user_id, data)

            else:
                logger.warning(f"Unknown message type from {user_id}: {message_type}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from {user_id}: {message[:100]}")
        except Exception as e:
            logger.error(f"Error handling message from {user_id}: {e}")

    def register_handler(
        self,
        message_type: str,
        handler: Callable[[str, dict], Coroutine]
    ) -> None:
        """
        Register a handler for a specific message type.

        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self._handlers[message_type] = handler

    def get_connection_info(self, user_id: str) -> Optional[dict]:
        """
        Get information about a user's connection.

        Args:
            user_id: User identifier

        Returns:
            Connection info dict or None
        """
        conn = self._connections.get(user_id)
        if not conn:
            return None

        return {
            "user_id": conn.user_id,
            "player_tag": conn.player_tag,
            "connected_at": conn.connected_at.isoformat(),
            "subscriptions": list(conn.subscriptions),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            "active_connections": len(self._connections),
            "topics": {
                topic: len(subscribers)
                for topic, subscribers in self._subscriptions.items()
            },
            "handlers_registered": list(self._handlers.keys()),
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# =============================================================================
# Notification Helpers
# =============================================================================

async def notify_meta_update(data: dict[str, Any]) -> int:
    """
    Notify all users about a meta update.

    Args:
        data: Meta update data

    Returns:
        Number of users notified
    """
    return await websocket_manager.broadcast(
        NotificationType.META_UPDATE,
        data
    )


async def notify_goal_progress(
    user_id: str,
    goal_id: int,
    progress: float,
    completed: bool = False
) -> bool:
    """
    Notify a user about goal progress.

    Args:
        user_id: User to notify
        goal_id: ID of the goal
        progress: Progress percentage (0-100)
        completed: Whether the goal was completed

    Returns:
        True if notification sent successfully
    """
    return await websocket_manager.send_notification(
        user_id,
        NotificationType.GOAL_PROGRESS,
        {
            "goal_id": goal_id,
            "progress": progress,
            "completed": completed,
        }
    )


async def notify_achievement(
    user_id: str,
    achievement_name: str,
    achievement_icon: str,
    description: str
) -> bool:
    """
    Notify a user about an unlocked achievement.

    Args:
        user_id: User to notify
        achievement_name: Name of the achievement
        achievement_icon: Icon identifier
        description: Achievement description

    Returns:
        True if notification sent successfully
    """
    return await websocket_manager.send_notification(
        user_id,
        NotificationType.ACHIEVEMENT_UNLOCKED,
        {
            "name": achievement_name,
            "icon": achievement_icon,
            "description": description,
        }
    )


async def notify_event_rotation(events: list[dict[str, Any]]) -> int:
    """
    Notify all users about event rotation change.

    Args:
        events: List of current events

    Returns:
        Number of users notified
    """
    return await websocket_manager.broadcast(
        NotificationType.EVENT_ROTATION,
        {"events": events}
    )
