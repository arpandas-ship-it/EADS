from flask import Blueprint, request, jsonify
from database import get_connection
from datetime import datetime


tracking_api = Blueprint(
    "tracking_api",
    __name__,
    url_prefix="/api"
)


# ============================================================
# VALID EMERGENCY STATUS FLOW
# ============================================================

STATUS_FLOW = {
    "RECEIVED": ["VERIFIED", "CANCELLED"],

    "VERIFIED": ["DISPATCHED", "CANCELLED"],

    "DISPATCHED": ["EN_ROUTE", "CANCELLED"],

    "EN_ROUTE": ["ON_SCENE", "CANCELLED"],

    "ON_SCENE": ["TRANSPORTING", "COMPLETED"],

    "TRANSPORTING": ["COMPLETED"],

    "COMPLETED": [],

    "CANCELLED": []
}


# ============================================================
# UPDATE EMERGENCY TRACKING STATUS
# ============================================================

@tracking_api.route(
    "/tracking/emergency/<int:emergency_id>/status",
    methods=["PUT"]
)
@tracking_api.route(
    "/tracking/emergencies/<int:emergency_id>/status",
    methods=["PUT"]
)
def update_tracking_status(emergency_id):

    data = request.get_json(silent=True) or {}

    new_status = str(
        data.get("status", "")
    ).upper()

    changed_by = data.get(
        "changed_by",
        "SYSTEM"
    )

    notes = data.get(
        "notes",
        ""
    )


    # --------------------------------------------------------
    # Validate status
    # --------------------------------------------------------

    if new_status not in STATUS_FLOW:

        return jsonify({
            "success": False,
            "message": "Invalid emergency status"
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Get emergency
        # ----------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))

        emergency = cursor.fetchone()


        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404


        old_status = emergency["status"]


        # ----------------------------------------------------
        # Check allowed transition
        # ----------------------------------------------------

        allowed_next = STATUS_FLOW.get(
            old_status,
            []
        )


        if new_status not in allowed_next:

            return jsonify({
                "success": False,
                "message": "Invalid status transition",
                "current_status": old_status,
                "requested_status": new_status,
                "allowed_next_statuses": allowed_next
            }), 400


        # ----------------------------------------------------
        # Update emergency
        # ----------------------------------------------------

        if new_status == "VERIFIED":

            cursor.execute("""
                UPDATE emergencies

                SET
                    status = ?,
                    verified_at = CURRENT_TIMESTAMP

                WHERE id = ?
            """, (
                new_status,
                emergency_id
            ))


        elif new_status == "DISPATCHED":

            cursor.execute("""
                UPDATE emergencies

                SET
                    status = ?,
                    dispatched_at = CURRENT_TIMESTAMP

                WHERE id = ?
            """, (
                new_status,
                emergency_id
            ))


        elif new_status == "COMPLETED":

            cursor.execute("""
                UPDATE emergencies

                SET
                    status = ?,
                    completed_at = CURRENT_TIMESTAMP

                WHERE id = ?
            """, (
                new_status,
                emergency_id
            ))


        else:

            cursor.execute("""
                UPDATE emergencies

                SET status = ?

                WHERE id = ?
            """, (
                new_status,
                emergency_id
            ))


        # ----------------------------------------------------
        # Save history
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO emergency_history
            (
                emergency_id,
                old_status,
                new_status,
                changed_by,
                notes
            )

            VALUES (?, ?, ?, ?, ?)
        """, (
            emergency_id,
            old_status,
            new_status,
            changed_by,
            notes
        ))


        # ----------------------------------------------------
        # If ambulance exists, update ambulance status
        # ----------------------------------------------------

        ambulance_id = emergency["ambulance_id"]


        if ambulance_id:

            ambulance_status = None


            if new_status == "DISPATCHED":

                ambulance_status = "ASSIGNED"


            elif new_status == "EN_ROUTE":

                ambulance_status = "EN_ROUTE"


            elif new_status == "ON_SCENE":

                ambulance_status = "ON_SCENE"


            elif new_status == "TRANSPORTING":

                ambulance_status = "TRANSPORTING"


            elif new_status in [
                "COMPLETED",
                "CANCELLED"
            ]:

                ambulance_status = "AVAILABLE"


            if ambulance_status:

                cursor.execute("""
                    UPDATE ambulances

                    SET status = ?

                    WHERE id = ?
                """, (
                    ambulance_status,
                    ambulance_id
                ))


        # ----------------------------------------------------
        # Update dispatch record
        # ----------------------------------------------------

        if ambulance_id:

            if new_status == "ON_SCENE":

                cursor.execute("""
                    UPDATE dispatch_records

                    SET arrival_time = CURRENT_TIMESTAMP

                    WHERE emergency_id = ?

                    AND ambulance_id = ?

                    AND arrival_time IS NULL
                """, (
                    emergency_id,
                    ambulance_id
                ))


            elif new_status == "COMPLETED":

                cursor.execute("""
                    UPDATE dispatch_records

                    SET completion_time = CURRENT_TIMESTAMP

                    WHERE emergency_id = ?

                    AND ambulance_id = ?

                    AND completion_time IS NULL
                """, (
                    emergency_id,
                    ambulance_id
                ))


        conn.commit()


        return jsonify({

            "success": True,

            "message": "Tracking status updated",

            "emergency_id": emergency_id,

            "emergency_code":
                emergency["emergency_code"],

            "old_status": old_status,

            "new_status": new_status,

            "ambulance_id": ambulance_id

        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "Tracking update failed",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# GET LIVE TRACKING INFORMATION
# ============================================================

@tracking_api.route(
    "/tracking/emergency/<int:emergency_id>",
    methods=["GET"]
)
@tracking_api.route(
    "/tracking/emergencies/<int:emergency_id>",
    methods=["GET"]
)
def get_live_tracking(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                e.id AS emergency_id,

                e.emergency_code,

                e.emergency_type,

                e.priority,

                e.description,

                e.location AS emergency_location,

                e.latitude AS emergency_latitude,

                e.longitude AS emergency_longitude,

                e.status AS emergency_status,

                e.created_at,

                e.verified_at,

                e.dispatched_at,

                e.completed_at,

                a.id AS ambulance_id,

                a.ambulance_number,

                a.driver_name,

                a.contact_number,

                a.status AS ambulance_status,

                a.latitude AS ambulance_latitude,

                a.longitude AS ambulance_longitude,

                a.current_location,

                d.dispatch_time,

                d.arrival_time,

                d.completion_time

            FROM emergencies e

            LEFT JOIN ambulances a
                ON e.ambulance_id = a.id

            LEFT JOIN dispatch_records d
                ON e.id = d.emergency_id
                AND e.ambulance_id = d.ambulance_id

            WHERE e.id = ?

            ORDER BY d.id DESC

            LIMIT 1

        """, (emergency_id,))


        tracking = cursor.fetchone()


        if not tracking:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404


        return jsonify({
            "success": True,
            "tracking": dict(tracking)
        })


    finally:

        conn.close()


# ============================================================
# GET ALL ACTIVE TRACKING
# ============================================================

@tracking_api.route(
    "/tracking/active",
    methods=["GET"]
)
def get_active_tracking():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                e.id AS emergency_id,

                e.emergency_code,

                e.emergency_type,

                e.priority,

                e.location,

                e.latitude AS emergency_latitude,

                e.longitude AS emergency_longitude,

                e.status AS emergency_status,

                a.id AS ambulance_id,

                a.ambulance_number,

                a.driver_name,

                a.status AS ambulance_status,

                a.latitude AS ambulance_latitude,

                a.longitude AS ambulance_longitude,

                a.current_location,

                d.dispatch_time,

                d.arrival_time

            FROM emergencies e

            LEFT JOIN ambulances a
                ON e.ambulance_id = a.id

            LEFT JOIN dispatch_records d
                ON e.id = d.emergency_id

            WHERE e.status NOT IN (
                'COMPLETED',
                'CANCELLED'
            )

            ORDER BY

                CASE e.priority

                    WHEN 'CRITICAL' THEN 1

                    WHEN 'HIGH' THEN 2

                    WHEN 'MEDIUM' THEN 3

                    WHEN 'LOW' THEN 4

                END,

                e.created_at ASC
        """)


        tracking = [
            dict(row)
            for row in cursor.fetchall()
        ]


        return jsonify({

            "success": True,

            "count": len(tracking),

            "active_tracking": tracking

        })


    finally:

        conn.close()


# ============================================================
# UPDATE LIVE AMBULANCE LOCATION
# ============================================================

@tracking_api.route(
    "/tracking/ambulance/<int:ambulance_id>/location",
    methods=["PUT"]
)
@tracking_api.route(
    "/tracking/ambulances/<int:ambulance_id>/location",
    methods=["PUT"]
)
def update_tracking_location(ambulance_id):

    data = request.get_json(silent=True) or {}


    latitude = data.get("latitude")
    longitude = data.get("longitude")
    location = data.get("location")


    # --------------------------------------------------------
    # Validate coordinates
    # --------------------------------------------------------

    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": (
                "Latitude and longitude "
                "are required"
            )
        }), 400


    try:

        latitude = float(latitude)
        longitude = float(longitude)

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message": "Invalid coordinates"
        }), 400


    if latitude < -90 or latitude > 90:

        return jsonify({
            "success": False,
            "message": "Invalid latitude"
        }), 400


    if longitude < -180 or longitude > 180:

        return jsonify({
            "success": False,
            "message": "Invalid longitude"
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Check ambulance
        # ----------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM ambulances
            WHERE id = ?
        """, (ambulance_id,))


        ambulance = cursor.fetchone()


        if not ambulance:

            return jsonify({
                "success": False,
                "message": "Ambulance not found"
            }), 404


        # ----------------------------------------------------
        # Update location
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE ambulances

            SET
                latitude = ?,
                longitude = ?,
                current_location = ?

            WHERE id = ?
        """, (
            latitude,
            longitude,
            location,
            ambulance_id
        ))


        conn.commit()


        return jsonify({

            "success": True,

            "message":
                "Ambulance location updated",

            "ambulance_id":
                ambulance_id,

            "latitude":
                latitude,

            "longitude":
                longitude,

            "location":
                location

        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "Location update failed",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# GET AMBULANCE CURRENT LOCATION
# ============================================================

@tracking_api.route(
    "/tracking/ambulances/<int:ambulance_id>",
    methods=["GET"]
)
def get_ambulance_tracking(ambulance_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                id,

                ambulance_number,

                driver_name,

                contact_number,

                ambulance_type,

                status,

                latitude,

                longitude,

                current_location

            FROM ambulances

            WHERE id = ?
        """, (ambulance_id,))


        ambulance = cursor.fetchone()


        if not ambulance:

            return jsonify({
                "success": False,
                "message": "Ambulance not found"
            }), 404


        return jsonify({

            "success": True,

            "ambulance": dict(ambulance)

        })


    finally:

        conn.close()


# ============================================================
# RESPONSE TIME
# ============================================================

@tracking_api.route(
    "/tracking/emergencies/<int:emergency_id>/response-time",
    methods=["GET"]
)
def get_response_time(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                id,

                emergency_code,

                created_at,

                dispatched_at,

                completed_at

            FROM emergencies

            WHERE id = ?
        """, (emergency_id,))


        emergency = cursor.fetchone()


        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404


        created = emergency["created_at"]
        dispatched = emergency["dispatched_at"]
        completed = emergency["completed_at"]


        # ----------------------------------------------------
        # Calculate response time
        # ----------------------------------------------------

        response_seconds = None


        if created and dispatched:

            created_time = datetime.strptime(
                created,
                "%Y-%m-%d %H:%M:%S"
            )

            dispatched_time = datetime.strptime(
                dispatched,
                "%Y-%m-%d %H:%M:%S"
            )

            response_seconds = int(
                (
                    dispatched_time
                    - created_time
                ).total_seconds()
            )


        # ----------------------------------------------------
        # Calculate total case duration
        # ----------------------------------------------------

        total_seconds = None


        if created and completed:

            created_time = datetime.strptime(
                created,
                "%Y-%m-%d %H:%M:%S"
            )

            completed_time = datetime.strptime(
                completed,
                "%Y-%m-%d %H:%M:%S"
            )

            total_seconds = int(
                (
                    completed_time
                    - created_time
                ).total_seconds()
            )


        return jsonify({

            "success": True,

            "emergency_id":
                emergency_id,

            "emergency_code":
                emergency["emergency_code"],

            "response_time_seconds":
                response_seconds,

            "total_case_duration_seconds":
                total_seconds

        })


    finally:

        conn.close()