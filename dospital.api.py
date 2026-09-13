from flask import Blueprint, request, jsonify
from database import get_connection
from math import radians, sin, cos, sqrt, atan2


hospital_api = Blueprint(
    "hospital_api",
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

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


# ============================================================
# GET ALL HOSPITALS
# ============================================================

@hospital_api.route(
    "/hospitals",
    methods=["GET"]
)
def get_hospitals():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        emergency_only = request.args.get(
            "emergency_only"
        )

        query = """
            SELECT *
            FROM hospitals
            WHERE 1 = 1
        """

        params = []

        if emergency_only == "true":

            query += """
                AND emergency_available = 1
            """

        query += """
            ORDER BY hospital_name ASC
        """

        cursor.execute(
            query,
            params
        )

        hospitals = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({
            "success": True,
            "count": len(hospitals),
            "hospitals": hospitals
        })

    finally:

        conn.close()


# ============================================================
# GET SINGLE HOSPITAL
# ============================================================

@hospital_api.route(
    "/hospitals/<int:hospital_id>",
    methods=["GET"]
)
def get_hospital(hospital_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT *
            FROM hospitals
            WHERE id = ?
        """, (hospital_id,))

        hospital = cursor.fetchone()

        if not hospital:

            return jsonify({
                "success": False,
                "message": "Hospital not found"
            }), 404

        return jsonify({
            "success": True,
            "hospital": dict(hospital)
        })

    finally:

        conn.close()


# ============================================================
# FIND SUITABLE HOSPITAL
# ============================================================

@hospital_api.route(
    "/hospitals/nearest",
    methods=["GET"]
)
def find_nearest_hospital():

    latitude = request.args.get(
        "latitude",
        type=float
    )

    longitude = request.args.get(
        "longitude",
        type=float
    )

    require_icu = request.args.get(
        "require_icu",
        "false"
    ).lower() == "true"


    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": (
                "Latitude and longitude "
                "are required"
            )
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Find hospitals with capacity
        # ----------------------------------------------------

        if require_icu:

            cursor.execute("""
                SELECT *
                FROM hospitals

                WHERE emergency_available = 1

                AND available_beds > 0

                AND icu_available > 0
            """)

        else:

            cursor.execute("""
                SELECT *
                FROM hospitals

                WHERE emergency_available = 1

                AND available_beds > 0
            """)


        hospitals = cursor.fetchall()


        if not hospitals:

            return jsonify({
                "success": False,
                "message": (
                    "No suitable hospital "
                    "is currently available"
                )
            }), 404


        nearest = None
        shortest_distance = float("inf")


        for hospital in hospitals:

            distance = calculate_distance(
                latitude,
                longitude,
                hospital["latitude"],
                hospital["longitude"]
            )


            if distance < shortest_distance:

                shortest_distance = distance
                nearest = hospital


        return jsonify({

            "success": True,

            "hospital": dict(nearest),

            "distance_km":
                round(shortest_distance, 2),

            "icu_required":
                require_icu

        })


    finally:

        conn.close()


# ============================================================
# ASSIGN HOSPITAL TO EMERGENCY
# ============================================================

@hospital_api.route(
    "/emergencies/<int:emergency_id>/hospital",
    methods=["POST"]
)
def assign_hospital(emergency_id):

    data = request.get_json(
        silent=True
    ) or {}


    hospital_id = data.get(
        "hospital_id"
    )

    require_icu = bool(
        data.get(
            "require_icu",
            False
        )
    )

    assigned_by = data.get(
        "assigned_by",
        "SYSTEM"
    )


    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Find emergency
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
        # Check if hospital already assigned
        # ----------------------------------------------------

        if emergency["hospital_id"]:

            return jsonify({
                "success": False,
                "message": (
                    "A hospital is already "
                    "assigned to this emergency"
                )
            }), 409


        # ----------------------------------------------------
        # If hospital ID provided, validate it
        # ----------------------------------------------------

        if hospital_id:

            if require_icu:

                cursor.execute("""
                    SELECT *
                    FROM hospitals

                    WHERE id = ?

                    AND emergency_available = 1

                    AND available_beds > 0

                    AND icu_available > 0
                """, (hospital_id,))

            else:

                cursor.execute("""
                    SELECT *
                    FROM hospitals

                    WHERE id = ?

                    AND emergency_available = 1

                    AND available_beds > 0
                """, (hospital_id,))


            hospital = cursor.fetchone()


            if not hospital:

                return jsonify({
                    "success": False,
                    "message": (
                        "Selected hospital is "
                        "not suitable or unavailable"
                    )
                }), 409


        # ====================================================
        # AUTOMATIC HOSPITAL SELECTION
        # ====================================================

        else:

            if require_icu:

                cursor.execute("""
                    SELECT *
                    FROM hospitals

                    WHERE emergency_available = 1

                    AND available_beds > 0

                    AND icu_available > 0
                """)

            else:

                cursor.execute("""
                    SELECT *
                    FROM hospitals

                    WHERE emergency_available = 1

                    AND available_beds > 0
                """)


            hospitals = cursor.fetchall()


            if not hospitals:

                return jsonify({
                    "success": False,
                    "message": (
                        "No suitable hospital "
                        "is available"
                    )
                }), 409


            nearest = None
            shortest_distance = float("inf")


            for candidate in hospitals:

                distance = calculate_distance(
                    emergency["latitude"],
                    emergency["longitude"],
                    candidate["latitude"],
                    candidate["longitude"]
                )


                if distance < shortest_distance:

                    shortest_distance = distance
                    nearest = candidate


            hospital = nearest
            hospital_id = hospital["id"]


        # ----------------------------------------------------
        # Reserve hospital capacity
        # ----------------------------------------------------

        if require_icu:

            cursor.execute("""
                UPDATE hospitals

                SET
                    available_beds =
                        available_beds - 1,

                    icu_available =
                        icu_available - 1

                WHERE id = ?

                AND available_beds > 0

                AND icu_available > 0
            """, (hospital_id,))

        else:

            cursor.execute("""
                UPDATE hospitals

                SET
                    available_beds =
                        available_beds - 1

                WHERE id = ?

                AND available_beds > 0
            """, (hospital_id,))


        if cursor.rowcount == 0:

            conn.rollback()

            return jsonify({
                "success": False,
                "message": (
                    "Hospital capacity changed "
                    "while assigning"
                )
            }), 409


        # ----------------------------------------------------
        # Link hospital with emergency
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE emergencies

            SET hospital_id = ?

            WHERE id = ?
        """, (
            hospital_id,
            emergency_id
        ))


        # ----------------------------------------------------
        # Save emergency history
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
            emergency["status"],
            assigned_by,
            (
                f"Hospital assigned: "
                f"{hospital['hospital_name']}"
            )
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
                    hospital["phone"],

                "beds_reserved":
                    1,

                "icu_reserved":
                    1 if require_icu else 0

            }

        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "Hospital assignment failed",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# UPDATE HOSPITAL CAPACITY
# ============================================================

@hospital_api.route(
    "/hospitals/<int:hospital_id>/capacity",
    methods=["PUT"]
)
def update_capacity(hospital_id):

    data = request.get_json(
        silent=True
    ) or {}


    available_beds = data.get(
        "available_beds"
    )

    icu_available = data.get(
        "icu_available"
    )


    if available_beds is None:

        return jsonify({
            "success": False,
            "message":
                "available_beds is required"
        }), 400


    try:

        available_beds = int(
            available_beds
        )

        if icu_available is not None:

            icu_available = int(
                icu_available
            )

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message":
                "Capacity values must be integers"
        }), 400


    if available_beds < 0:

        return jsonify({
            "success": False,
            "message":
                "Available beds cannot be negative"
        }), 400


    if icu_available is not None:

        if icu_available < 0:

            return jsonify({
                "success": False,
                "message":
                    "ICU availability cannot be negative"
            }), 400


        if icu_available > available_beds:

            return jsonify({
                "success": False,
                "message":
                    "ICU count cannot exceed available beds"
            }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM hospitals
            WHERE id = ?
        """, (hospital_id,))


        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "Hospital not found"
            }), 404


        if icu_available is None:

            cursor.execute("""
                UPDATE hospitals

                SET available_beds = ?

                WHERE id = ?
            """, (
                available_beds,
                hospital_id
            ))

        else:

            cursor.execute("""
                UPDATE hospitals

                SET
                    available_beds = ?,
                    icu_available = ?

                WHERE id = ?
            """, (
                available_beds,
                icu_available,
                hospital_id
            ))


        conn.commit()


        return jsonify({

            "success": True,

            "message":
                "Hospital capacity updated",

            "hospital_id":
                hospital_id,

            "available_beds":
                available_beds,

            "icu_available":
                icu_available

        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message":
                "Capacity update failed",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# UPDATE HOSPITAL EMERGENCY AVAILABILITY
# ============================================================

@hospital_api.route(
    "/hospitals/<int:hospital_id>/availability",
    methods=["PUT"]
)
def update_hospital_availability(hospital_id):

    data = request.get_json(
        silent=True
    ) or {}


    emergency_available = data.get(
        "emergency_available"
    )


    if emergency_available is None:

        return jsonify({
            "success": False,
            "message":
                "emergency_available is required"
        }), 400


    emergency_available = bool(
        emergency_available
    )


    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM hospitals
            WHERE id = ?
        """, (hospital_id,))


        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "Hospital not found"
            }), 404


        cursor.execute("""
            UPDATE hospitals

            SET emergency_available = ?

            WHERE id = ?
        """, (
            1 if emergency_available else 0,
            hospital_id
        ))


        conn.commit()


        return jsonify({

            "success": True,

            "message":
                "Hospital emergency availability updated",

            "hospital_id":
                hospital_id,

            "emergency_available":
                emergency_available

        })


    finally:

        conn.close()


# ============================================================
# GET HOSPITAL EMERGENCIES
# ============================================================

@hospital_api.route(
    "/hospitals/<int:hospital_id>/emergencies",
    methods=["GET"]
)
def hospital_emergencies(hospital_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                e.id,
                e.emergency_code,
                e.caller_name,
                e.emergency_type,
                e.priority,
                e.location,
                e.status,
                e.created_at,
                e.completed_at,

                a.ambulance_number,
                a.driver_name

            FROM emergencies e

            LEFT JOIN ambulances a
                ON e.ambulance_id = a.id

            WHERE e.hospital_id = ?

            ORDER BY e.created_at DESC
        """, (hospital_id,))


        emergencies = [
            dict(row)
            for row in cursor.fetchall()
        ]


        return jsonify({

            "success": True,

            "hospital_id":
                hospital_id,

            "count":
                len(emergencies),

            "emergencies":
                emergencies

        })


    finally:

        conn.close()


# ============================================================
# RELEASE HOSPITAL BED
# ============================================================

@hospital_api.route(
    "/emergencies/<int:emergency_id>/release-bed",
    methods=["POST"]
)
def release_hospital_bed(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Find emergency and hospital
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                hospital_id,
                status

            FROM emergencies

            WHERE id = ?
        """, (emergency_id,))


        emergency = cursor.fetchone()


        if not emergency:

            return jsonify({
                "success": False,
                "message":
                    "Emergency not found"
            }), 404


        hospital_id = emergency["hospital_id"]


        if not hospital_id:

            return jsonify({
                "success": False,
                "message":
                    "No hospital assigned"
            }), 400


        if emergency["status"] != "COMPLETED":

            return jsonify({
                "success": False,
                "message":
                    "Bed can only be released after completion"
            }), 400


        # ----------------------------------------------------
        # Increase available bed count
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE hospitals

            SET available_beds =
                available_beds + 1

            WHERE id = ?
        """, (hospital_id,))


        conn.commit()


        return jsonify({

            "success": True,

            "message":
                "Hospital bed released",

            "emergency_id":
                emergency_id,

            "hospital_id":
                hospital_id

        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message":
                "Failed to release hospital bed",
            "error": str(e)
        }), 500

    finally:

        conn.close()