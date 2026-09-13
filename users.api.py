from flask import Blueprint, request, jsonify
from database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash


user_api = Blueprint(
    "user_api",
    __name__,
    url_prefix="/api"
)


# ============================================================
# VALID ROLES
# ============================================================

VALID_ROLES = {
    "ADMIN",
    "DISPATCHER",
    "DRIVER",
    "HOSPITAL"
}


# ============================================================
# CREATE USER
# ============================================================

@user_api.route("/users", methods=["POST"])
def create_user():

    data = request.get_json(silent=True) or {}

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = str(data.get("role", "")).upper()
    phone = data.get("phone", "")

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if not name or not email or not password or not role:

        return jsonify({
            "success": False,
            "message": "Name, email, password and role are required"
        }), 400

    if role not in VALID_ROLES:

        return jsonify({
            "success": False,
            "message": "Invalid user role",
            "allowed_roles": list(VALID_ROLES)
        }), 400

    if len(password) < 6:

        return jsonify({
            "success": False,
            "message": "Password must contain at least 6 characters"
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Check existing email
        # ----------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM users
            WHERE email = ?
        """, (email,))

        if cursor.fetchone():

            return jsonify({
                "success": False,
                "message": "Email already registered"
            }), 409


        # ----------------------------------------------------
        # Hash password
        # ----------------------------------------------------

        password_hash = generate_password_hash(
            password
        )


        # ----------------------------------------------------
        # Create user
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO users
            (
                name,
                email,
                password,
                role,
                phone,
                status
            )

            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        """, (
            name,
            email,
            password_hash,
            role,
            phone
        ))


        user_id = cursor.lastrowid

        conn.commit()


        return jsonify({

            "success": True,

            "message":
                "User created successfully",

            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "role": role,
                "phone": phone,
                "status": "ACTIVE"
            }

        }), 201


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "User creation failed",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# LOGIN
# ============================================================

@user_api.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")


    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email,))

        user = cursor.fetchone()


        if not user:

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401


        # ----------------------------------------------------
        # Check account status
        # ----------------------------------------------------

        if user["status"] != "ACTIVE":

            return jsonify({
                "success": False,
                "message": "User account is not active"
            }), 403


        # ----------------------------------------------------
        # Verify password
        # ----------------------------------------------------

        if not check_password_hash(
            user["password"],
            password
        ):

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401


        return jsonify({

            "success": True,

            "message":
                "Login successful",

            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "phone": user["phone"],
                "status": user["status"]
            }

        })


    finally:

        conn.close()


# ============================================================
# GET ALL USERS
# ============================================================

@user_api.route("/users", methods=["GET"])
def get_users():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        role = request.args.get("role")
        status = request.args.get("status")


        query = """
            SELECT
                id,
                name,
                email,
                role,
                phone,
                status,
                created_at

            FROM users

            WHERE 1 = 1
        """

        params = []


        if role:

            query += """
                AND role = ?
            """

            params.append(
                role.upper()
            )


        if status:

            query += """
                AND status = ?
            """

            params.append(
                status.upper()
            )


        query += """
            ORDER BY created_at DESC
        """


        cursor.execute(
            query,
            params
        )


        users = [
            dict(row)
            for row in cursor.fetchall()
        ]


        return jsonify({

            "success": True,

            "count":
                len(users),

            "users":
                users

        })


    finally:

        conn.close()


# ============================================================
# GET SINGLE USER
# ============================================================

@user_api.route(
    "/users/<int:user_id>",
    methods=["GET"]
)
def get_user(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                role,
                phone,
                status,
                created_at

            FROM users

            WHERE id = ?
        """, (user_id,))


        user = cursor.fetchone()


        if not user:

            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404


        return jsonify({

            "success": True,

            "user":
                dict(user)

        })


    finally:

        conn.close()


# ============================================================
# UPDATE USER
# ============================================================

@user_api.route(
    "/users/<int:user_id>",
    methods=["PUT"]
)
def update_user(user_id):

    data = request.get_json(silent=True) or {}


    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT *
            FROM users
            WHERE id = ?
        """, (user_id,))


        user = cursor.fetchone()


        if not user:

            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404


        name = data.get(
            "name",
            user["name"]
        )

        email = data.get(
            "email",
            user["email"]
        )

        phone = data.get(
            "phone",
            user["phone"]
        )

        role = str(
            data.get(
                "role",
                user["role"]
            )
        ).upper()

        status = str(
            data.get(
                "status",
                user["status"]
            )
        ).upper()


        if role not in VALID_ROLES:

            return jsonify({
                "success": False,
                "message": "Invalid role"
            }), 400


        if status not in [
            "ACTIVE",
            "INACTIVE"
        ]:

            return jsonify({
                "success": False,
                "message": "Invalid account status"
            }), 400


        # ----------------------------------------------------
        # Check duplicate email
        # ----------------------------------------------------

        cursor.execute("""
            SELECT id

            FROM users

            WHERE email = ?

            AND id != ?
        """, (
            email,
            user_id
        ))


        if cursor.fetchone():

            return jsonify({
                "success": False,
                "message": "Email already used by another user"
            }), 409


        # ----------------------------------------------------
        # Update
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE users

            SET
                name = ?,
                email = ?,
                role = ?,
                phone = ?,
                status = ?

            WHERE id = ?
        """, (
            name,
            email,
            role,
            phone,
            status,
            user_id
        ))


        conn.commit()


        return jsonify({

            "success": True,

            "message":
                "User updated successfully",

            "user_id":
                user_id

        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": "User update failed",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# CHANGE PASSWORD
# ============================================================

@user_api.route(
    "/users/<int:user_id>/password",
    methods=["PUT"]
)
def change_password(user_id):

    data = request.get_json(silent=True) or {}


    old_password = data.get(
        "old_password"
    )

    new_password = data.get(
        "new_password"
    )


    if not old_password or not new_password:

        return jsonify({
            "success": False,
            "message":
                "Old and new passwords are required"
        }), 400


    if len(new_password) < 6:

        return jsonify({
            "success": False,
            "message":
                "New password must contain at least 6 characters"
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT *
            FROM users
            WHERE id = ?
        """, (user_id,))


        user = cursor.fetchone()


        if not user:

            return jsonify({
                "success": False,
                "message":
                    "User not found"
            }), 404


        if not check_password_hash(
            user["password"],
            old_password
        ):

            return jsonify({
                "success": False,
                "message":
                    "Current password is incorrect"
            }), 401


        new_hash = generate_password_hash(
            new_password
        )


        cursor.execute("""
            UPDATE users

            SET password = ?

            WHERE id = ?
        """, (
            new_hash,
            user_id
        ))


        conn.commit()


        return jsonify({

            "success": True,

            "message":
                "Password changed successfully"

        })


    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message":
                "Password change failed",
            "error": str(e)
        }), 500

    finally:

        conn.close()


# ============================================================
# ACTIVATE / DEACTIVATE USER
# ============================================================

@user_api.route(
    "/users/<int:user_id>/status",
    methods=["PUT"]
)
def change_user_status(user_id):

    data = request.get_json(silent=True) or {}

    status = str(
        data.get("status", "")
    ).upper()


    if status not in [
        "ACTIVE",
        "INACTIVE"
    ]:

        return jsonify({
            "success": False,
            "message":
                "Status must be ACTIVE or INACTIVE"
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT id
            FROM users
            WHERE id = ?
        """, (user_id,))


        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "User not found"
            }), 404


        cursor.execute("""
            UPDATE users

            SET status = ?

            WHERE id = ?
        """, (
            status,
            user_id
        ))


        conn.commit()


        return jsonify({

            "success": True,

            "message":
                "User status updated",

            "user_id":
                user_id,

            "status":
                status

        })


    finally:

        conn.close()


# ============================================================
# USER STATISTICS
# ============================================================

@user_api.route(
    "/users/stats",
    methods=["GET"]
)
def user_stats():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM users
        """)

        total = cursor.fetchone()["total"]


        cursor.execute("""
            SELECT COUNT(*) AS active
            FROM users
            WHERE status = 'ACTIVE'
        """)

        active = cursor.fetchone()["active"]


        cursor.execute("""
            SELECT
                role,
                COUNT(*) AS count

            FROM users

            GROUP BY role
        """)


        role_breakdown = {
            row["role"]: row["count"]
            for row in cursor.fetchall()
        }


        return jsonify({

            "success": True,

            "statistics": {

                "total_users":
                    total,

                "active_users":
                    active,

                "inactive_users":
                    total - active,

                "role_breakdown":
                    role_breakdown
            }

        })


    finally:

        conn.close()