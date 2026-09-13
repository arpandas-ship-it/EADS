# notification_api.py

from flask import Blueprint, request, jsonify
from database import get_connection
from datetime import datetime


notification_api = Blueprint(
    "notification_api",
    __name__,
    url_prefix="/api/notifications"
)


# ============================================================
# CREATE NOTIFICATION
# ============================================================

def create_notification(
    title,
    message,
    notification_type="INFO",
    emergency_id=None,
    user_id=None
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute("""
            INSERT INTO notifications
            (
                user_id,
                emergency_id,
                title,
                message,
                notification_type,
                is_read,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            emergency_id,
            title,
            message,
            notification_type,
            0,
            now
        ))

        notification_id = cursor.lastrowid

        conn.commit()

        return {
            "success": True,
            "notification_id": notification_id
        }

    except Exception as e:

        conn.rollback()

        return {
            "success": False,
            "message": str(e)
        }

    finally:

        conn.close()


# ============================================================
# GET NOTIFICATIONS
# ============================================================

@notification_api.route(
    "",
    methods=["GET"]
)
def get_notifications():

    user_id = request.args.get(
        "user_id",
        type=int
    )

    limit = request.args.get(
        "limit",
        50,
        type=int
    )

    # Prevent unnecessarily large requests
    limit = min(max(limit, 1), 100)

    conn = get_connection()
    cursor = conn.cursor()

    try:

        if user_id:

            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    emergency_id,
                    title,
                    message,
                    notification_type,
                    is_read,
                    created_at
                FROM notifications
                WHERE user_id = ?
                   OR user_id IS NULL
                ORDER BY created_at DESC
                LIMIT ?
            """, (
                user_id,
                limit
            ))

        else:

            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    emergency_id,
                    title,
                    message,
                    notification_type,
                    is_read,
                    created_at
                FROM notifications
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        notifications = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "count":
                len(notifications),

            "notifications":
                notifications

        })

    finally:

        conn.close()


# ============================================================
# GET UNREAD NOTIFICATIONS
# ============================================================

@notification_api.route(
    "/unread",
    methods=["GET"]
)
def get_unread_notifications():

    user_id = request.args.get(
        "user_id",
        type=int
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        if user_id:

            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    emergency_id,
                    title,
                    message,
                    notification_type,
                    is_read,
                    created_at
                FROM notifications
                WHERE is_read = 0
                AND (
                    user_id = ?
                    OR user_id IS NULL
                )
                ORDER BY created_at DESC
            """, (user_id,))

        else:

            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    emergency_id,
                    title,
                    message,
                    notification_type,
                    is_read,
                    created_at
                FROM notifications
                WHERE is_read = 0
                ORDER BY created_at DESC
            """)

        notifications = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "unread_count":
                len(notifications),

            "notifications":
                notifications

        })

    finally:

        conn.close()


# ============================================================
# MARK ONE NOTIFICATION AS READ
# ============================================================

@notification_api.route(
    "/<int:notification_id>/read",
    methods=["PUT"]
)
def mark_as_read(notification_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM notifications
            WHERE id = ?
        """, (notification_id,))

        notification = cursor.fetchone()

        if not notification:

            return jsonify({

                "success": False,

                "message":
                    "Notification not found"

            }), 404

        cursor.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
        """, (notification_id,))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Notification marked as read",

            "notification_id":
                notification_id

        })

    finally:

        conn.close()


# ============================================================
# MARK ALL AS READ
# ============================================================

@notification_api.route(
    "/read-all",
    methods=["PUT"]
)
def mark_all_as_read():

    user_id = request.args.get(
        "user_id",
        type=int
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        if user_id:

            cursor.execute("""
                UPDATE notifications
                SET is_read = 1
                WHERE user_id = ?
                   OR user_id IS NULL
            """, (user_id,))

        else:

            cursor.execute("""
                UPDATE notifications
                SET is_read = 1
                WHERE is_read = 0
            """)

        updated = cursor.rowcount

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Notifications marked as read",

            "updated":
                updated

        })

    finally:

        conn.close()


# ============================================================
# DELETE NOTIFICATION
# ============================================================

@notification_api.route(
    "/<int:notification_id>",
    methods=["DELETE"]
)
def delete_notification(notification_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            DELETE FROM notifications
            WHERE id = ?
        """, (notification_id,))

        if cursor.rowcount == 0:

            return jsonify({

                "success": False,

                "message":
                    "Notification not found"

            }), 404

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Notification deleted"

        })

    finally:

        conn.close()


# ============================================================
# EMERGENCY NOTIFICATION
# ============================================================

@notification_api.route(
    "/emergency",
    methods=["POST"]
)
def emergency_notification():

    data = request.get_json()

    if not data:

        return jsonify({

            "success": False,

            "message":
                "Request body is required"

        }), 400

    emergency_id = data.get(
        "emergency_id"
    )

    title = data.get(
        "title",
        "Emergency Alert"
    )

    message = data.get(
        "message",
        "Emergency case requires attention."
    )

    notification_type = data.get(
        "notification_type",
        "EMERGENCY"
    )

    user_id = data.get(
        "user_id"
    )

    result = create_notification(
        title=title,
        message=message,
        notification_type=notification_type,
        emergency_id=emergency_id,
        user_id=user_id
    )

    if not result["success"]:

        return jsonify(result), 500

    return jsonify({

        "success": True,

        "message":
            "Emergency notification created",

        "notification_id":
            result["notification_id"]

    }), 201