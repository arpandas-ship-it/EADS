# reports_api.py

from flask import Blueprint, jsonify, request
from database import get_connection


reports_api = Blueprint(
    "reports_api",
    __name__,
    url_prefix="/api/reports"
)


# ============================================================
# SUMMARY REPORT
# ============================================================

@reports_api.route("/summary", methods=["GET"])
def summary_report():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # TOTAL EMERGENCIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergencies
        """)

        total_emergencies = cursor.fetchone()["total"]

        # ----------------------------------------------------
        # ACTIVE EMERGENCIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergencies
            WHERE status NOT IN (
                'COMPLETED',
                'CANCELLED'
            )
        """)

        active_emergencies = cursor.fetchone()["total"]

        # ----------------------------------------------------
        # COMPLETED EMERGENCIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergencies
            WHERE status = 'COMPLETED'
        """)

        completed_emergencies = cursor.fetchone()["total"]

        # ----------------------------------------------------
        # CRITICAL EMERGENCIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergencies
            WHERE priority = 'CRITICAL'
        """)

        critical_emergencies = cursor.fetchone()["total"]

        # ----------------------------------------------------
        # CANCELLED EMERGENCIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergencies
            WHERE status = 'CANCELLED'
        """)

        cancelled_emergencies = cursor.fetchone()["total"]

        # ----------------------------------------------------
        # DISPATCHED EMERGENCIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergencies
            WHERE dispatched_at IS NOT NULL
        """)

        dispatched_emergencies = cursor.fetchone()["total"]

        return jsonify({

            "success": True,

            "summary": {

                "total_emergencies":
                    total_emergencies,

                "active_emergencies":
                    active_emergencies,

                "completed_emergencies":
                    completed_emergencies,

                "critical_emergencies":
                    critical_emergencies,

                "cancelled_emergencies":
                    cancelled_emergencies,

                "dispatched_emergencies":
                    dispatched_emergencies
            }

        })

    finally:

        conn.close()


# ============================================================
# EMERGENCY STATUS REPORT
# ============================================================

@reports_api.route(
    "/emergency-status",
    methods=["GET"]
)
def emergency_status_report():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                status,
                COUNT(*) AS count
            FROM emergencies
            GROUP BY status
            ORDER BY count DESC
        """)

        results = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "status_report":
                results

        })

    finally:

        conn.close()


# ============================================================
# PRIORITY REPORT
# ============================================================

@reports_api.route(
    "/priority",
    methods=["GET"]
)
def priority_report():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                priority,
                COUNT(*) AS count
            FROM emergencies
            GROUP BY priority
            ORDER BY
                CASE priority
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                    ELSE 5
                END
        """)

        results = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "priority_report":
                results

        })

    finally:

        conn.close()


# ============================================================
# EMERGENCY TYPE REPORT
# ============================================================

@reports_api.route(
    "/types",
    methods=["GET"]
)
def emergency_type_report():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                emergency_type,
                COUNT(*) AS count
            FROM emergencies
            GROUP BY emergency_type
            ORDER BY count DESC
        """)

        results = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "emergency_types":
                results

        })

    finally:

        conn.close()


# ============================================================
# RESPONSE TIME REPORT
# ============================================================

@reports_api.route(
    "/response-time",
    methods=["GET"]
)
def response_time_report():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                id,
                emergency_code,
                priority,
                created_at,
                dispatched_at,

                ROUND(
                    (
                        julianday(dispatched_at)
                        -
                        julianday(created_at)
                    ) * 60,
                    2
                ) AS response_minutes

            FROM emergencies

            WHERE
                created_at IS NOT NULL
                AND dispatched_at IS NOT NULL

            ORDER BY created_at DESC
        """)

        records = [
            dict(row)
            for row in cursor.fetchall()
        ]

        # ----------------------------------------------------
        # AVERAGE RESPONSE TIME
        # ----------------------------------------------------

        cursor.execute("""
            SELECT

                ROUND(
                    AVG(
                        (
                            julianday(dispatched_at)
                            -
                            julianday(created_at)
                        ) * 60
                    ),
                    2
                ) AS average_response_minutes

            FROM emergencies

            WHERE
                created_at IS NOT NULL
                AND dispatched_at IS NOT NULL
        """)

        average = cursor.fetchone()

        return jsonify({

            "success": True,

            "average_response_minutes":
                average[
                    "average_response_minutes"
                ],

            "records":
                records

        })

    finally:

        conn.close()


# ============================================================
# AMBULANCE UTILIZATION
# ============================================================

@reports_api.route(
    "/ambulances",
    methods=["GET"]
)
def ambulance_report():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                a.id,
                a.ambulance_number,
                a.ambulance_type,
                a.driver_name,
                a.status,

                COUNT(d.id) AS total_dispatches

            FROM ambulances a

            LEFT JOIN dispatch_records d
                ON a.id = d.ambulance_id

            GROUP BY a.id

            ORDER BY total_dispatches DESC
        """)

        results = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "ambulances":
                results

        })

    finally:

        conn.close()


# ============================================================
# HOSPITAL REPORT
# ============================================================

@reports_api.route(
    "/hospitals",
    methods=["GET"]
)
def hospital_report():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                h.id,
                h.hospital_name,
                h.emergency_available,
                h.available_beds,
                h.icu_available,

                COUNT(e.id) AS emergency_cases

            FROM hospitals h

            LEFT JOIN emergencies e
                ON h.id = e.hospital_id

            GROUP BY h.id

            ORDER BY emergency_cases DESC
        """)

        results = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "hospitals":
                results

        })

    finally:

        conn.close()


# ============================================================
# DAILY EMERGENCY REPORT
# ============================================================

@reports_api.route(
    "/daily",
    methods=["GET"]
)
def daily_report():

    days = request.args.get(
        "days",
        7,
        type=int
    )

    days = min(
        max(days, 1),
        365
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                DATE(created_at) AS date,

                COUNT(*) AS total_emergencies,

                SUM(
                    CASE
                        WHEN priority = 'CRITICAL'
                        THEN 1
                        ELSE 0
                    END
                ) AS critical_cases,

                SUM(
                    CASE
                        WHEN status = 'COMPLETED'
                        THEN 1
                        ELSE 0
                    END
                ) AS completed_cases

            FROM emergencies

            WHERE DATE(created_at)
                >= DATE(
                    'now',
                    ?
                )

            GROUP BY DATE(created_at)

            ORDER BY date ASC
        """, (
            f"-{days} days",
        ))

        results = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "days":
                days,

            "daily_report":
                results

        })

    finally:

        conn.close()


# ============================================================
# CRITICAL CASE REPORT
# ============================================================

@reports_api.route(
    "/critical",
    methods=["GET"]
)
def critical_cases():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                e.id,
                e.emergency_code,
                e.caller_name,
                e.caller_phone,
                e.emergency_type,
                e.priority,
                e.location,
                e.status,
                e.created_at,
                e.dispatched_at,
                e.completed_at,

                a.ambulance_number,
                a.driver_name,

                h.hospital_name

            FROM emergencies e

            LEFT JOIN ambulances a
                ON e.ambulance_id = a.id

            LEFT JOIN hospitals h
                ON e.hospital_id = h.id

            WHERE e.priority = 'CRITICAL'

            ORDER BY e.created_at DESC
        """)

        results = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return jsonify({

            "success": True,

            "count":
                len(results),

            "critical_cases":
                results

        })

    finally:

        conn.close()


# ============================================================
# SYSTEM HEALTH
# ============================================================

@reports_api.route(
    "/system-health",
    methods=["GET"]
)
def system_health():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # AMBULANCES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN status = 'AVAILABLE'
                        THEN 1 ELSE 0
                    END
                ) AS available
            FROM ambulances
        """)

        ambulance = dict(
            cursor.fetchone()
        )

        # ----------------------------------------------------
        # HOSPITALS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN emergency_available = 1
                        THEN 1 ELSE 0
                    END
                ) AS available
            FROM hospitals
        """)

        hospital = dict(
            cursor.fetchone()
        )

        # ----------------------------------------------------
        # ACTIVE EMERGENCIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergencies
            WHERE status NOT IN (
                'COMPLETED',
                'CANCELLED'
            )
        """)

        active = cursor.fetchone()["total"]

        # ----------------------------------------------------
        # USERS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM users
            WHERE status = 'ACTIVE'
        """)

        active_users = cursor.fetchone()["total"]

        return jsonify({

            "success": True,

            "system_health": {

                "ambulances": ambulance,

                "hospitals": hospital,

                "active_emergencies":
                    active,

                "active_users":
                    active_users
            }

        })

    finally:

        conn.close()