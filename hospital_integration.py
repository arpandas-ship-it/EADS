# hospital_integration.py

from flask import Blueprint, request, jsonify
from database import get_connection
from emergency_validation import is_valid_transition
from datetime import datetime
import math


hospital_integration = Blueprint(
    "hospital_integration",
    __name__,
    url_prefix="/api/hospital-integration"
)


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

    R = 6371

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return R * c


# ============================================================
# FIND SUITABLE HOSPITAL
# ============================================================

def find_suitable_hospital(
    latitude,
    longitude,
    requires_icu=False
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # GET AVAILABLE HOSPITALS
        # ----------------------------------------------------

        if requires_icu:

            cursor.execute("""
                SELECT
                    id,
                    hospital_name,
                    address,
                    phone,
                    emergency_available,
                    available_beds,
                    icu_available,
                    latitude,
                    longitude
                FROM hospitals
                WHERE emergency_available = 1
                AND (
                    available_beds > 0
                    OR icu_available > 0
                )
            """)

        else:

            cursor.execute("""
                SELECT
                    id,
                    hospital_name,
                    address,
                    phone,
                    emergency_available,
                    available_beds,
                    icu_available,
                    latitude,
                    longitude
                FROM hospitals
                WHERE emergency_available = 1
                AND available_beds > 0
            """)

        hospitals = cursor.fetchall()

        results = []

        for hospital in hospitals:

            distance = calculate_distance(
                latitude,
                longitude,
                hospital["latitude"],
                hospital["longitude"]
            )

            item = dict(hospital)

            item["distance_km"] = round(
                distance,
                2
            )

            results.append(item)

        # Nearest hospital first
        results.sort(
            key=lambda x: x["distance_km"]
        )

        return results

    finally:

        conn.close()


# ============================================================
# FIND HOSPITALS FOR AN EMERGENCY
# ============================================================

@hospital_integration.route(
    "/emergency/<int:emergency_id>/hospitals",
    methods=["GET"]
)
def find_hospitals_for_emergency(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                emergency_code,
                emergency_type,
                priority,
                status,
                latitude,
                longitude
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))

        emergency = cursor.fetchone()

        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404

        # ----------------------------------------------------
        # ICU REQUIREMENT
        # ----------------------------------------------------

        requires_icu = (
            emergency["emergency_type"]
            and "ICU" in emergency["emergency_type"].upper()
        )

        hospitals = find_suitable_hospital(
            emergency["latitude"],
            emergency["longitude"],
            requires_icu
        )

        return jsonify({

            "success": True,

            "emergency_id":
                emergency["id"],

            "emergency_code":
                emergency["emergency_code"],

            "hospitals":
                hospitals

        })

    finally:

        conn.close()


# ============================================================
# ASSIGN HOSPITAL
# ============================================================

@hospital_integration.route(
    "/emergency/<int:emergency_id>/assign",
    methods=["PUT"]
)
def assign_hospital(emergency_id):

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    hospital_id = data.get("hospital_id")

    changed_by = data.get(
        "changed_by",
        "DISPATCHER"
    )

    if not hospital_id:

        return jsonify({
            "success": False,
            "message": "hospital_id is required"
        }), 400

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
                emergency_type,
                priority,
                status,
                hospital_id,
                latitude,
                longitude
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))

        emergency = cursor.fetchone()

        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404

        # ----------------------------------------------------
        # CHECK STATUS
        # ----------------------------------------------------

        if emergency["status"] not in [
            "ON_SCENE",
            "TRANSPORTING"
        ]:

            return jsonify({

                "success": False,

                "message":
                    "Hospital can only be assigned when "
                    "the emergency is ON_SCENE or TRANSPORTING",

                "current_status":
                    emergency["status"]

            }), 400

        # ----------------------------------------------------
        # CHECK HOSPITAL
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                hospital_name,
                address,
                phone,
                emergency_available,
                available_beds,
                icu_available
            FROM hospitals
            WHERE id = ?
        """, (hospital_id,))

        hospital = cursor.fetchone()

        if not hospital:

            return jsonify({
                "success": False,
                "message": "Hospital not found"
            }), 404

        # ----------------------------------------------------
        # CHECK EMERGENCY AVAILABILITY
        # ----------------------------------------------------

        if not hospital["emergency_available"]:

            return jsonify({

                "success": False,

                "message":
                    "Hospital is not accepting emergencies"

            }), 400

        # ----------------------------------------------------
        # CHECK CAPACITY
        # ----------------------------------------------------

        requires_icu = (
            emergency["emergency_type"]
            and "ICU" in emergency["emergency_type"].upper()
        )

        if requires_icu:

            if hospital["icu_available"] <= 0:

                return jsonify({

                    "success": False,

                    "message":
                        "No ICU capacity available"

                }), 400

        else:

            if hospital["available_beds"] <= 0:

                return jsonify({

                    "success": False,

                    "message":
                        "No hospital bed available"

                }), 400

        # ----------------------------------------------------
        # CHECK IF ALREADY ASSIGNED
        # ----------------------------------------------------

        if emergency["hospital_id"]:

            return jsonify({

                "success": False,

                "message":
                    "A hospital is already assigned",

                "hospital_id":
                    emergency["hospital_id"]

            }), 400

        # ----------------------------------------------------
        # ASSIGN HOSPITAL
        # ----------------------------------------------------

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute("""
            UPDATE emergencies
            SET hospital_id = ?
            WHERE id = ?
        """, (
            hospital_id,
            emergency_id
        ))

        # ----------------------------------------------------
        # UPDATE CAPACITY
        # ----------------------------------------------------

        if requires_icu:

            cursor.execute("""
                UPDATE hospitals
                SET icu_available =
                    icu_available - 1
                WHERE id = ?
                AND icu_available > 0
            """, (hospital_id,))

        else:

            cursor.execute("""
                UPDATE hospitals
                SET available_beds =
                    available_beds - 1
                WHERE id = ?
                AND available_beds > 0
            """, (hospital_id,))

        # ----------------------------------------------------
        # SAVE HISTORY
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO emergency_history
            (
                emergency_id,
                old_status,
                new_status,
                changed_by,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            emergency_id,
            emergency["status"],
            emergency["status"],
            changed_by,
            "Hospital assigned: "
            + hospital["hospital_name"],
            now
        ))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Hospital assigned successfully",

            "emergency_id":
                emergency_id,

            "hospital": {

                "id":
                    hospital["id"],

                "name":
                    hospital["hospital_name"],

                "address":
                    hospital["address"],

                "phone":
                    hospital["phone"]
            },

            "assigned_at":
                now

        })

    except Exception as e:

        conn.rollback()

        return jsonify({

            "success": False,

            "message":
                "Hospital assignment failed",

            "error":
                str(e)

        }), 500

    finally:

        conn.close()


# ============================================================
# MOVE EMERGENCY TO TRANSPORTING
# ============================================================

@hospital_integration.route(
    "/emergency/<int:emergency_id>/transport",
    methods=["PUT"]
)
def start_transport(emergency_id):

    data = request.get_json() or {}

    changed_by = data.get(
        "changed_by",
        "DRIVER"
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                emergency_code,
                status,
                hospital_id,
                ambulance_id
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))

        emergency = cursor.fetchone()

        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404

        # ----------------------------------------------------
        # HOSPITAL MUST BE ASSIGNED
        # ----------------------------------------------------

        if not emergency["hospital_id"]:

            return jsonify({

                "success": False,

                "message":
                    "Assign a hospital before transportation"

            }), 400

        # ----------------------------------------------------
        # CHECK STATUS TRANSITION
        # ----------------------------------------------------

        if not is_valid_transition(
            emergency["status"],
            "TRANSPORTING"
        ):

            return jsonify({

                "success": False,

                "message":
                    f"Invalid transition: "
                    f"{emergency['status']} → TRANSPORTING"

            }), 400

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----------------------------------------------------
        # UPDATE EMERGENCY
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE emergencies
            SET status = ?
            WHERE id = ?
        """, (
            "TRANSPORTING",
            emergency_id
        ))

        # ----------------------------------------------------
        # UPDATE AMBULANCE
        # ----------------------------------------------------

        if emergency["ambulance_id"]:

            cursor.execute("""
                UPDATE ambulances
                SET status = 'TRANSPORTING'
                WHERE id = ?
            """, (
                emergency["ambulance_id"],
            ))

        # ----------------------------------------------------
        # SAVE HISTORY
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO emergency_history
            (
                emergency_id,
                old_status,
                new_status,
                changed_by,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            emergency_id,
            emergency["status"],
            "TRANSPORTING",
            changed_by,
            "Patient transportation started",
            now
        ))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Emergency marked as TRANSPORTING",

            "emergency_id":
                emergency_id,

            "status":
                "TRANSPORTING",

            "hospital_id":
                emergency["hospital_id"],

            "updated_at":
                now

        })

    except Exception as e:

        conn.rollback()

        return jsonify({

            "success": False,

            "message":
                "Failed to start transportation",

            "error":
                str(e)

        }), 500

    finally:

        conn.close()


# ============================================================
# COMPLETE EMERGENCY AT HOSPITAL
# ============================================================

@hospital_integration.route(
    "/emergency/<int:emergency_id>/complete",
    methods=["PUT"]
)
def complete_emergency(emergency_id):

    data = request.get_json() or {}

    changed_by = data.get(
        "changed_by",
        "HOSPITAL"
    )

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
                ambulance_id,
                hospital_id
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))

        emergency = cursor.fetchone()

        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404

        # ----------------------------------------------------
        # CHECK HOSPITAL
        # ----------------------------------------------------

        if not emergency["hospital_id"]:

            return jsonify({

                "success": False,

                "message":
                    "No hospital is assigned"

            }), 400

        # ----------------------------------------------------
        # CHECK STATUS
        # ----------------------------------------------------

        if not is_valid_transition(
            emergency["status"],
            "COMPLETED"
        ):

            return jsonify({

                "success": False,

                "message":
                    f"Emergency must be TRANSPORTING "
                    f"before completion. "
                    f"Current status: "
                    f"{emergency['status']}"

            }), 400

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----------------------------------------------------
        # COMPLETE EMERGENCY
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE emergencies
            SET
                status = 'COMPLETED',
                completed_at = ?
            WHERE id = ?
        """, (
            now,
            emergency_id
        ))

        # ----------------------------------------------------
        # RELEASE AMBULANCE
        # ----------------------------------------------------

        if emergency["ambulance_id"]:

            cursor.execute("""
                UPDATE ambulances
                SET status = 'AVAILABLE'
                WHERE id = ?
            """, (
                emergency["ambulance_id"],
            ))

        # ----------------------------------------------------
        # CLOSE DISPATCH
        # ----------------------------------------------------

        if emergency["ambulance_id"]:

            cursor.execute("""
                UPDATE dispatch_records
                SET status = 'COMPLETED'
                WHERE emergency_id = ?
                AND ambulance_id = ?
                AND status = 'ACTIVE'
            """, (
                emergency_id,
                emergency["ambulance_id"]
            ))

        # ----------------------------------------------------
        # SAVE HISTORY
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO emergency_history
            (
                emergency_id,
                old_status,
                new_status,
                changed_by,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            emergency_id,
            emergency["status"],
            "COMPLETED",
            changed_by,
            "Emergency case completed at hospital",
            now
        ))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Emergency case completed successfully",

            "emergency_id":
                emergency_id,

            "status":
                "COMPLETED",

            "ambulance_status":
                "AVAILABLE",

            "completed_at":
                now

        })

    except Exception as e:

        conn.rollback()

        return jsonify({

            "success": False,

            "message":
                "Failed to complete emergency",

            "error":
                str(e)

        }), 500

    finally:

        conn.close()


# ============================================================
# GET HOSPITAL INFORMATION FOR EMERGENCY
# ============================================================

@hospital_integration.route(
    "/emergency/<int:emergency_id>",
    methods=["GET"]
)
def get_emergency_hospital(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                e.id AS emergency_id,
                e.emergency_code,
                e.status AS emergency_status,

                h.id AS hospital_id,
                h.hospital_name,
                h.address,
                h.phone,
                h.emergency_available,
                h.available_beds,
                h.icu_available,
                h.latitude,
                h.longitude

            FROM emergencies e

            LEFT JOIN hospitals h
                ON e.hospital_id = h.id

            WHERE e.id = ?
        """, (emergency_id,))

        result = cursor.fetchone()

        if not result:

            return jsonify({

                "success": False,

                "message":
                    "Emergency not found"

            }), 404

        return jsonify({

            "success": True,

            "hospital":
                dict(result)

        })

    finally:

        conn.close()