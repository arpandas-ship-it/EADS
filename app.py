from flask import Flask, request, jsonify
from flask_cors import CORS
from database import get_connection, init_database
from datetime import datetime

app = Flask(__name__)
CORS(app)


# ============================================================
# EMERGENCY PRIORITY VALIDATION
# ============================================================

VALID_PRIORITIES = {
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW"
}

VALID_STATUSES = {
    "RECEIVED",
    "VERIFIED",
    "DISPATCHED",
    "EN_ROUTE",
    "ON_SCENE",
    "TRANSPORTING",
    "COMPLETED",
    "CANCELLED"
}


# ============================================================
# GENERATE EMERGENCY ID
# ============================================================

def generate_emergency_code(cursor):

    cursor.execute("""
        SELECT emergency_code
        FROM emergencies
        ORDER BY id DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    if not result:
        number = 1001
    else:
        last_code = result["emergency_code"]

        try:
            number = int(last_code.split("-")[1]) + 1
        except:
            number = 1001

    return f"E-{number}"


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "success": True,
        "message": "EADS Emergency API is running",
        "timestamp": datetime.now().isoformat()
    })


# ============================================================
# CREATE EMERGENCY
# ============================================================

@app.route("/api/emergencies", methods=["POST"])
def create_emergency():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    required_fields = [
        "caller_name",
        "caller_phone",
        "emergency_type",
        "priority",
        "location"
    ]

    missing_fields = [
        field for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:

        return jsonify({
            "success": False,
            "message": "Required fields are missing",
            "missing_fields": missing_fields
        }), 400


    # --------------------------------------------------------
    # Validate priority
    # --------------------------------------------------------

    priority = str(data["priority"]).upper()

    if priority not in VALID_PRIORITIES:

        return jsonify({
            "success": False,
            "message": "Invalid emergency priority",
            "allowed": list(VALID_PRIORITIES)
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        emergency_code = generate_emergency_code(cursor)

        cursor.execute("""
            INSERT INTO emergencies
            (
                emergency_code,
                caller_name,
                caller_phone,
                emergency_type,
                priority,
                description,
                location,
                latitude,
                longitude,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            emergency_code,

            data["caller_name"],

            data["caller_phone"],

            data["emergency_type"],

            priority,

            data.get("description", ""),

            data["location"],

            data.get("latitude"),

            data.get("longitude"),

            "RECEIVED"
        ))


        emergency_id = cursor.lastrowid


        # ----------------------------------------------------
        # Create initial emergency history
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
            None,
            "RECEIVED",
            data.get("created_by", "SYSTEM"),
            "Emergency request received"
        ))


        conn.commit()


        # ----------------------------------------------------
        # Get created emergency
        # ----------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))

        emergency = dict(cursor.fetchone())


        return jsonify({
            "success": True,
            "message": "Emergency created successfully",
            "emergency": emergency
        }), 201


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create emergency",
            "error": str(e)
        }), 500

    finally:
        conn.close()


# ============================================================
# GET ALL EMERGENCIES
# ============================================================

@app.route("/api/emergencies", methods=["GET"])
def get_emergencies():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # Optional filters
        status = request.args.get("status")
        priority = request.args.get("priority")

        query = """
            SELECT
                e.*,
                a.ambulance_number,
                h.hospital_name
            FROM emergencies e

            LEFT JOIN ambulances a
                ON e.ambulance_id = a.id

            LEFT JOIN hospitals h
                ON e.hospital_id = h.id

            WHERE 1 = 1
        """

        params = []


        if status:

            query += " AND e.status = ?"

            params.append(status.upper())


        if priority:

            query += " AND e.priority = ?"

            params.append(priority.upper())


        query += """
            ORDER BY
                CASE e.priority
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                END,
                e.created_at DESC
        """


        cursor.execute(query, params)

        emergencies = [
            dict(row)
            for row in cursor.fetchall()
        ]


        return jsonify({
            "success": True,
            "count": len(emergencies),
            "emergencies": emergencies
        })


    finally:
        conn.close()


# ============================================================
# GET SINGLE EMERGENCY
# ============================================================

@app.route("/api/emergencies/<int:emergency_id>", methods=["GET"])
def get_emergency(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                e.*,
                a.ambulance_number,
                a.driver_name,
                a.contact_number AS ambulance_contact,

                h.hospital_name,
                h.address AS hospital_address,
                h.phone AS hospital_phone

            FROM emergencies e

            LEFT JOIN ambulances a
                ON e.ambulance_id = a.id

            LEFT JOIN hospitals h
                ON e.hospital_id = h.id

            WHERE e.id = ?
        """, (emergency_id,))


        emergency = cursor.fetchone()


        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404


        return jsonify({
            "success": True,
            "emergency": dict(emergency)
        })


    finally:
        conn.close()


# ============================================================
# UPDATE EMERGENCY STATUS
# ============================================================

@app.route(
    "/api/emergencies/<int:emergency_id>/status",
    methods=["PUT"]
)
def update_emergency_status(emergency_id):

    data = request.get_json()

    if not data or not data.get("status"):

        return jsonify({
            "success": False,
            "message": "New status is required"
        }), 400


    new_status = str(data["status"]).upper()


    if new_status not in VALID_STATUSES:

        return jsonify({
            "success": False,
            "message": "Invalid emergency status",
            "allowed": list(VALID_STATUSES)
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Get current emergency
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
        # Don't update if status is unchanged
        # ----------------------------------------------------

        if old_status == new_status:

            return jsonify({
                "success": False,
                "message": f"Emergency is already {new_status}"
            }), 400


        # ----------------------------------------------------
        # Update timestamp depending on status
        # ----------------------------------------------------

        if new_status == "VERIFIED":

            cursor.execute("""
                UPDATE emergencies
                SET status = ?,
                    verified_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, emergency_id))


        elif new_status == "DISPATCHED":

            cursor.execute("""
                UPDATE emergencies
                SET status = ?,
                    dispatched_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, emergency_id))


        elif new_status == "COMPLETED":

            cursor.execute("""
                UPDATE emergencies
                SET status = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, emergency_id))


        else:

            cursor.execute("""
                UPDATE emergencies
                SET status = ?
                WHERE id = ?
            """, (new_status, emergency_id))


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
            data.get("changed_by", "SYSTEM"),
            data.get("notes", "")
        ))


        conn.commit()


        return jsonify({
            "success": True,
            "message": "Emergency status updated",
            "emergency_id": emergency_id,
            "old_status": old_status,
            "new_status": new_status
        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to update status",
            "error": str(e)
        }), 500

    finally:
        conn.close()


# ============================================================
# GET EMERGENCY HISTORY
# ============================================================

@app.route(
    "/api/emergencies/<int:emergency_id>/history",
    methods=["GET"]
)
def get_emergency_history(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # Check emergency
        cursor.execute("""
            SELECT id
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))


        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404


        cursor.execute("""
            SELECT
                id,
                old_status,
                new_status,
                changed_by,
                notes,
                changed_at

            FROM emergency_history

            WHERE emergency_id = ?

            ORDER BY changed_at ASC
        """, (emergency_id,))


        history = [
            dict(row)
            for row in cursor.fetchall()
        ]


        return jsonify({
            "success": True,
            "emergency_id": emergency_id,
            "history": history
        })


    finally:
        conn.close()


# ============================================================
# DASHBOARD EMERGENCY STATISTICS
# ============================================================

@app.route("/api/emergencies/stats", methods=["GET"])
def emergency_stats():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Total emergencies
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergencies
        """)

        total = cursor.fetchone()["total"]


        # ----------------------------------------------------
        # Active emergencies
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS active
            FROM emergencies

            WHERE status NOT IN (
                'COMPLETED',
                'CANCELLED'
            )
        """)

        active = cursor.fetchone()["active"]


        # ----------------------------------------------------
        # Critical emergencies
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS critical
            FROM emergencies

            WHERE priority = 'CRITICAL'

            AND status NOT IN (
                'COMPLETED',
                'CANCELLED'
            )
        """)

        critical = cursor.fetchone()["critical"]


        # ----------------------------------------------------
        # Priority breakdown
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                priority,
                COUNT(*) AS count

            FROM emergencies

            GROUP BY priority
        """)

        priority_breakdown = {
            row["priority"]: row["count"]
            for row in cursor.fetchall()
        }


        # ----------------------------------------------------
        # Status breakdown
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                status,
                COUNT(*) AS count

            FROM emergencies

            GROUP BY status
        """)

        status_breakdown = {
            row["status"]: row["count"]
            for row in cursor.fetchall()
        }


        return jsonify({
            "success": True,

            "statistics": {
                "total_emergencies": total,
                "active_emergencies": active,
                "critical_emergencies": critical,
                "priority_breakdown": priority_breakdown,
                "status_breakdown": status_breakdown
            }
        })


    finally:
        conn.close()


# ============================================================
# DELETE / CANCEL EMERGENCY
# ============================================================

@app.route(
    "/api/emergencies/<int:emergency_id>/cancel",
    methods=["PUT"]
)
def cancel_emergency(emergency_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT status
            FROM emergencies
            WHERE id = ?
        """, (emergency_id,))


        emergency = cursor.fetchone()


        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency not found"
            }), 404


        if emergency["status"] in [
            "COMPLETED",
            "CANCELLED"
        ]:

            return jsonify({
                "success": False,
                "message": "Emergency cannot be cancelled"
            }), 400


        old_status = emergency["status"]


        cursor.execute("""
            UPDATE emergencies

            SET status = 'CANCELLED'

            WHERE id = ?
        """, (emergency_id,))


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
            "CANCELLED",
            "SYSTEM",
            "Emergency cancelled"
        ))


        conn.commit()


        return jsonify({
            "success": True,
            "message": "Emergency cancelled successfully"
        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to cancel emergency",
            "error": str(e)
        }), 500

    finally:
        conn.close()


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    # Create database/tables if they don't exist
    init_database()

    print("\n======================================")
    print(" EADS EMERGENCY DISPATCH SYSTEM")
    print(" Emergency API Server")
    print("======================================")
    print("Server: http://127.0.0.1:5000")
    print("======================================\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )