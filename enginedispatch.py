# dispatch_engine.py

import math
import importlib.util
from database import get_connection
from datetime import datetime
from pathlib import Path


_validation_path = Path(__file__).with_name("emergency.validation.py")
_validation_spec = importlib.util.spec_from_file_location(
    "emergency_validation",
    _validation_path
)
if _validation_spec is None or _validation_spec.loader is None:
    raise ImportError(f"Unable to load validation module: {_validation_path}")

_validation_module = importlib.util.module_from_spec(_validation_spec)
_validation_spec.loader.exec_module(_validation_module)
is_valid_transition = _validation_module.is_valid_transition


# ============================================================
# DISTANCE CALCULATION
# ============================================================

def calculate_distance(lat1, lon1, lat2, lon2):

    if None in (lat1, lon1, lat2, lon2):
        return float("inf")

    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
    except (ValueError, TypeError):
        return float("inf")

    # Earth's radius in kilometres
    R = 6371

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return R * c


# ============================================================
# FIND AVAILABLE AMBULANCES
# ============================================================

def find_available_ambulances(
    emergency_latitude,
    emergency_longitude
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                ambulance_number,
                ambulance_type,
                driver_name,
                contact_number,
                status,
                latitude,
                longitude
            FROM ambulances
            WHERE status = 'AVAILABLE'
        """)

        ambulances = cursor.fetchall()

        results = []

        for ambulance in ambulances:

            distance = calculate_distance(
                emergency_latitude,
                emergency_longitude,
                ambulance["latitude"],
                ambulance["longitude"]
            )

            ambulance_data = dict(ambulance)

            ambulance_data["distance_km"] = round(
                distance,
                2
            )

            results.append(ambulance_data)

        # Nearest ambulance first
        results.sort(
            key=lambda x: x["distance_km"]
        )

        return results

    finally:

        conn.close()


# ============================================================
# GET BEST AMBULANCE
# ============================================================

def get_best_ambulance(
    emergency_latitude,
    emergency_longitude
):

    ambulances = find_available_ambulances(
        emergency_latitude,
        emergency_longitude
    )

    if not ambulances:
        return None

    return ambulances[0]


# ============================================================
# DISPATCH AMBULANCE
# ============================================================

def dispatch_ambulance(
    emergency_id,
    ambulance_id=None,
    changed_by="SYSTEM"
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # GET EMERGENCY
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                emergency_code,
                status,
                latitude,
                longitude,
                ambulance_id
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))

        emergency = cursor.fetchone()

        if not emergency:

            return {
                "success": False,
                "message": "Emergency not found"
            }

        # ----------------------------------------------------
        # CHECK STATUS
        # ----------------------------------------------------

        if emergency["status"] != "VERIFIED":

            return {
                "success": False,
                "message":
                    "Only VERIFIED emergencies can be dispatched",
                "current_status":
                    emergency["status"]
            }

        # ----------------------------------------------------
        # CHECK WHETHER AMBULANCE WAS PROVIDED
        # ----------------------------------------------------

        if ambulance_id:

            cursor.execute("""
                SELECT
                    id,
                    ambulance_number,
                    ambulance_type,
                    driver_name,
                    contact_number,
                    status,
                    latitude,
                    longitude
                FROM ambulances
                WHERE id = ?
            """, (ambulance_id,))

            ambulance = cursor.fetchone()

            if not ambulance:

                return {
                    "success": False,
                    "message": "Ambulance not found"
                }

            # ------------------------------------------------
            # CHECK AVAILABILITY
            # ------------------------------------------------

            if ambulance["status"] != "AVAILABLE":

                return {
                    "success": False,
                    "message":
                        "Selected ambulance is not available",
                    "ambulance_status":
                        ambulance["status"]
                }

        else:

            # ------------------------------------------------
            # AUTOMATIC DISPATCH
            # ------------------------------------------------

            ambulance = get_best_ambulance(
                emergency["latitude"],
                emergency["longitude"]
            )

            if not ambulance:

                return {
                    "success": False,
                    "message":
                        "No available ambulance found"
                }

            ambulance_id = ambulance["id"]

        # ----------------------------------------------------
        # CHECK STATUS TRANSITION
        # ----------------------------------------------------

        if not is_valid_transition(
            emergency["status"],
            "DISPATCHED"
        ):

            return {
                "success": False,
                "message":
                    "Invalid emergency status transition"
            }

        # ----------------------------------------------------
        # UPDATE EMERGENCY
        # ----------------------------------------------------

        dispatched_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute("""
            UPDATE emergencies
            SET
                status = 'DISPATCHED',
                ambulance_id = ?,
                dispatched_at = ?
            WHERE id = ?
        """, (
            ambulance_id,
            dispatched_time,
            emergency_id
        ))

        # ----------------------------------------------------
        # UPDATE AMBULANCE
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE ambulances
            SET status = 'ASSIGNED'
            WHERE id = ?
        """, (ambulance_id,))

        # ----------------------------------------------------
        # SAVE STATUS HISTORY
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO emergency_history
            (
                emergency_id,
                old_status,
                new_status,
                changed_by,
                notes,
                changed_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            emergency_id,
            "VERIFIED",
            "DISPATCHED",
            changed_by,
            "Ambulance dispatched successfully",
            dispatched_time
        ))

        # ----------------------------------------------------
        # CREATE DISPATCH RECORD
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO dispatch_records
            (
                emergency_id,
                ambulance_id,
                dispatch_time
            )
            VALUES (?, ?, ?)
        """, (
            emergency_id,
            ambulance_id,
            dispatched_time
        ))

        conn.commit()

        return {
            "success": True,
            "message":
                "Ambulance dispatched successfully",
            "emergency_id":
                emergency_id,
            "ambulance_id":
                ambulance_id,
            "ambulance_number":
                ambulance["ambulance_number"],
            "status":
                "DISPATCHED",
            "dispatched_at":
                dispatched_time
        }

    except Exception as e:

        conn.rollback()

        return {
            "success": False,
            "message":
                "Dispatch failed",
            "error":
                str(e)
        }

    finally:

        conn.close()


# ============================================================
# GET DISPATCH INFORMATION
# ============================================================

def get_dispatch_info(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                e.id AS emergency_id,
                e.emergency_code,
                e.status AS emergency_status,
                e.ambulance_id,

                a.ambulance_number,
                a.ambulance_type,
                a.driver_name,
                a.contact_number,
                a.status AS ambulance_status,
                a.latitude AS ambulance_latitude,
                a.longitude AS ambulance_longitude,

                d.dispatch_time AS dispatched_at,
                CASE
                    WHEN e.status IN ('DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'TRANSPORTING')
                    THEN 'ACTIVE'
                    ELSE 'COMPLETED'
                END AS dispatch_status

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

        result = cursor.fetchone()

        if not result:

            return None

        return dict(result)

    finally:

        conn.close()


# ============================================================
# GET ALL ACTIVE DISPATCHES
# ============================================================

def get_active_dispatches():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                e.id AS emergency_id,
                e.emergency_code,
                e.priority,
                e.location,
                e.status AS emergency_status,

                a.id AS ambulance_id,
                a.ambulance_number,
                a.driver_name,
                a.status AS ambulance_status,

                d.dispatch_time AS dispatched_at,
                'ACTIVE' AS dispatch_status

            FROM dispatch_records d

            INNER JOIN emergencies e
                ON d.emergency_id = e.id

            INNER JOIN ambulances a
                ON d.ambulance_id = a.id

            WHERE e.status IN ('DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'TRANSPORTING')

            ORDER BY
                CASE e.priority
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                    ELSE 5
                END,

                d.dispatch_time ASC
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:

        conn.close()


# ============================================================
# RELEASE AMBULANCE
# ============================================================

def release_ambulance(
    ambulance_id,
    emergency_id=None
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT id, status
            FROM ambulances
            WHERE id = ?
        """, (ambulance_id,))

        ambulance = cursor.fetchone()

        if not ambulance:

            return {
                "success": False,
                "message": "Ambulance not found"
            }

        # ----------------------------------------------------
        # MAKE AMBULANCE AVAILABLE
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE ambulances
            SET status = 'AVAILABLE'
            WHERE id = ?
        """, (ambulance_id,))

        # ----------------------------------------------------
        # CLOSE DISPATCH RECORD
        # ----------------------------------------------------

        if emergency_id:

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

        return {
            "success": True,
            "message":
                "Ambulance released successfully",
            "ambulance_id":
                ambulance_id,
            "status":
                "AVAILABLE"
        }

    except Exception as e:

        conn.rollback()

        return {
            "success": False,
            "message":
                "Failed to release ambulance",
            "error":
                str(e)
        }

    finally:

        conn.close()