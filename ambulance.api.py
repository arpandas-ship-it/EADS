from flask import Blueprint, request, jsonify
from database import get_connection
from math import radians, sin, cos, sqrt, atan2


ambulance_api = Blueprint(
    "ambulance_api",
    __name__,
    url_prefix="/api"
)


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def calculate_distance(lat1, lon1, lat2, lon2):

    if None in [lat1, lon1, lat2, lon2]:
        return 999999

    R = 6371.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)

    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        +
        cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


# ============================================================
# GET ALL AMBULANCES
# ============================================================

@ambulance_api.route(
    "/ambulances",
    methods=["GET"]
)
def get_ambulances():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        status = request.args.get("status")

        query = """
            SELECT *
            FROM ambulances
            WHERE 1 = 1
        """

        params = []

        if status:

            query += """
                AND status = ?
            """

            params.append(status.upper())

        query += """
            ORDER BY id ASC
        """

        cursor.execute(query, params)

        ambulances = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({
            "success": True,
            "count": len(ambulances),
            "ambulances": ambulances
        })

    finally:

        conn.close()


# ============================================================
# GET SINGLE AMBULANCE
# ============================================================

@ambulance_api.route(
    "/ambulances/<int:ambulance_id>",
    methods=["GET"]
)
def get_ambulance(ambulance_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

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

        return jsonify({
            "success": True,
            "ambulance": dict(ambulance)
        })

    finally:

        conn.close()


# ============================================================
# FIND NEAREST AVAILABLE AMBULANCE
# ============================================================

@ambulance_api.route(
    "/ambulances/nearest",
    methods=["GET"]
)
def find_nearest_ambulance():

    latitude = request.args.get("latitude", type=float)
    longitude = request.args.get("longitude", type=float)

    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": "Latitude and longitude are required"
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT *
            FROM ambulances
            WHERE status = 'AVAILABLE'
              AND latitude IS NOT NULL
              AND longitude IS NOT NULL
        """)

        ambulances = cursor.fetchall()

        if not ambulances:

            return jsonify({
                "success": False,
                "message": "No available ambulance found"
            }), 404

        nearest = None
        shortest_distance = float("inf")

        for ambulance in ambulances:

            distance = calculate_distance(
                latitude,
                longitude,
                ambulance["latitude"],
                ambulance["longitude"]
            )

            if distance < shortest_distance:

                shortest_distance = distance
                nearest = ambulance

        return jsonify({
            "success": True,
            "ambulance": dict(nearest),
            "distance_km": round(shortest_distance, 2)
        })

    finally:

        conn.close()


# ============================================================
# DISPATCH AMBULANCE TO EMERGENCY
# ============================================================

@ambulance_api.route(
    "/dispatch/emergency/<int:emergency_id>",
    methods=["POST"]
)
@ambulance_api.route(
    "/emergencies/<int:emergency_id>/dispatch",
    methods=["POST"]
)
def dispatch_ambulance(emergency_id):

    data = request.get_json(silent=True) or {}

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # FIND EMERGENCY
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


        # ----------------------------------------------------
        # CHECK EMERGENCY STATUS
        # ----------------------------------------------------

        if emergency["status"] in [
            "COMPLETED",
            "CANCELLED"
        ]:

            return jsonify({
                "success": False,
                "message": (
                    "This emergency is already "
                    + emergency["status"].lower()
                )
            }), 400


        if emergency["ambulance_id"]:

            return jsonify({
                "success": False,
                "message": "An ambulance is already assigned"
            }), 400


        # ----------------------------------------------------
        # SELECT AMBULANCE
        # ----------------------------------------------------

        ambulance_id = data.get("ambulance_id")


        # ====================================================
        # OPTION 1:
        # DISPATCHER SELECTS AMBULANCE
        # ====================================================

        if ambulance_id:

            cursor.execute("""
                SELECT *
                FROM ambulances
                WHERE id = ?
                  AND status = 'AVAILABLE'
            """, (ambulance_id,))

            ambulance = cursor.fetchone()

            if not ambulance:

                return jsonify({
                    "success": False,
                    "message": (
                        "Selected ambulance is not "
                        "available"
                    )
                }), 409


        # ====================================================
        # OPTION 2:
        # SYSTEM AUTOMATICALLY FINDS NEAREST AMBULANCE
        # ====================================================

        else:

            cursor.execute("""
                SELECT *
                FROM ambulances
                WHERE status = 'AVAILABLE'
            """)

            available = cursor.fetchall()

            if not available:

                return jsonify({
                    "success": False,
                    "message": (
                        "No available ambulance "
                        "for this emergency"
                    ),
                    "emergency_id": emergency_id,
                    "priority": emergency["priority"]
                }), 409


            nearest = None
            shortest_distance = float("inf")


            for candidate in available:

                distance = calculate_distance(
                    emergency["latitude"],
                    emergency["longitude"],
                    candidate["latitude"],
                    candidate["longitude"]
                )


                if distance < shortest_distance:

                    shortest_distance = distance
                    nearest = candidate


            ambulance = nearest

            ambulance_id = ambulance["id"]


        # ----------------------------------------------------
        # ASSIGN AMBULANCE
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE ambulances

            SET status = 'ASSIGNED'

            WHERE id = ?
              AND status = 'AVAILABLE'
        """, (ambulance_id,))


        if cursor.rowcount == 0:

            conn.rollback()

            return jsonify({
                "success": False,
                "message": (
                    "Ambulance became unavailable "
                    "during dispatch"
                )
            }), 409


        # ----------------------------------------------------
        # UPDATE EMERGENCY
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE emergencies

            SET
                ambulance_id = ?,
                status = 'DISPATCHED',
                dispatched_at = CURRENT_TIMESTAMP

            WHERE id = ?
        """, (
            ambulance_id,
            emergency_id
        ))


        # ----------------------------------------------------
        # CREATE DISPATCH RECORD
        # ----------------------------------------------------

        dispatcher_name = data.get(
            "dispatcher_name",
            "SYSTEM"
        )


        cursor.execute("""
            INSERT INTO dispatch_records
            (
                emergency_id,
                ambulance_id,
                dispatcher_name
            )

            VALUES (?, ?, ?)
        """, (
            emergency_id,
            ambulance_id,
            dispatcher_name
        ))


        # ----------------------------------------------------
        # SAVE EMERGENCY HISTORY
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
            emergency["status"],
            "DISPATCHED",
            dispatcher_name,
            f"Ambulance {ambulance['ambulance_number']} dispatched"
        ))


        conn.commit()


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "message": (
                "Ambulance dispatched successfully"
            ),

            "dispatch": {

                "emergency_id": emergency_id,

                "emergency_code":
                    emergency["emergency_code"],

                "priority":
                    emergency["priority"],

                "ambulance_id":
                    ambulance_id,

                "ambulance_number":
                    ambulance["ambulance_number"],

                "driver_name":
                    ambulance["driver_name"],

                "ambulance_status":
                    "ASSIGNED",

                "emergency_status":
                    "DISPATCHED"
            }

        }), 200


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "Dispatch failed",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# UPDATE AMBULANCE STATUS
# ============================================================

@ambulance_api.route(
    "/ambulances/<int:ambulance_id>/status",
    methods=["PUT"]
)
def update_ambulance_status(ambulance_id):

    data = request.get_json(silent=True) or {}

    status = str(
        data.get("status", "")
    ).upper()


    valid_statuses = {
        "AVAILABLE",
        "ASSIGNED",
        "EN_ROUTE",
        "ON_SCENE",
        "TRANSPORTING",
        "MAINTENANCE",
        "OFFLINE"
    }


    if status not in valid_statuses:

        return jsonify({
            "success": False,
            "message": "Invalid ambulance status",
            "allowed_statuses": list(valid_statuses)
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

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


        old_status = ambulance["status"]


        cursor.execute("""
            UPDATE ambulances

            SET status = ?

            WHERE id = ?
        """, (
            status,
            ambulance_id
        ))


        conn.commit()


        return jsonify({
            "success": True,
            "message": "Ambulance status updated",
            "ambulance_id": ambulance_id,
            "old_status": old_status,
            "new_status": status
        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to update ambulance",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# UPDATE AMBULANCE LOCATION
# ============================================================

@ambulance_api.route(
    "/ambulances/<int:ambulance_id>/location",
    methods=["PUT"]
)
def update_ambulance_location(ambulance_id):

    data = request.get_json(silent=True) or {}

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    location = data.get("location")


    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": (
                "Latitude and longitude are required"
            )
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM ambulances
            WHERE id = ?
        """, (ambulance_id,))


        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message": "Ambulance not found"
            }), 404


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
            "message": "Ambulance location updated",
            "ambulance_id": ambulance_id,
            "latitude": latitude,
            "longitude": longitude,
            "location": location
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
# GET ACTIVE DISPATCHES
# ============================================================

@ambulance_api.route(
    "/dispatches/active",
    methods=["GET"]
)
def get_active_dispatches():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                d.id AS dispatch_id,

                d.dispatch_time,

                e.id AS emergency_id,

                e.emergency_code,

                e.emergency_type,

                e.priority,

                e.location,

                e.status AS emergency_status,

                a.id AS ambulance_id,

                a.ambulance_number,

                a.driver_name,

                a.status AS ambulance_status,

                a.latitude,

                a.longitude

            FROM dispatch_records d

            INNER JOIN emergencies e
                ON d.emergency_id = e.id

            INNER JOIN ambulances a
                ON d.ambulance_id = a.id

            WHERE e.status NOT IN (
                'COMPLETED',
                'CANCELLED'
            )

            ORDER BY
                d.dispatch_time DESC
        """)


        dispatches = [
            dict(row)
            for row in cursor.fetchall()
        ]


        return jsonify({
            "success": True,
            "count": len(dispatches),
            "dispatches": dispatches
        })


    finally:

        conn.close()