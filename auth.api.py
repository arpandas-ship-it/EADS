from flask import Blueprint, request, jsonify
from database import get_connection
from werkzeug.security import check_password_hash
from functools import wraps
import jwt
import datetime
import os


auth_api = Blueprint(
    "auth_api",
    __name__,
    url_prefix="/api/auth"
)


# ============================================================
# SECRET KEY
# ============================================================

SECRET_KEY = os.environ.get(
    "EADS_SECRET_KEY",
    "EADS-DEVELOPMENT-SECRET-KEY"
)


# ============================================================
# LOGIN
# ============================================================

@auth_api.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                password,
                role,
                phone,
                status
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
        # CHECK ACCOUNT STATUS
        # ----------------------------------------------------

        if user["status"] != "ACTIVE":

            return jsonify({
                "success": False,
                "message": "User account is inactive"
            }), 403

        # ----------------------------------------------------
        # CHECK PASSWORD
        # ----------------------------------------------------

        if not check_password_hash(
            user["password"],
            password
        ):

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        # ----------------------------------------------------
        # CREATE TOKEN
        # ----------------------------------------------------

        payload = {

            "user_id": user["id"],

            "email": user["email"],

            "role": user["role"],

            "exp":
                datetime.datetime.utcnow()
                + datetime.timedelta(hours=8)
        }

        token = jwt.encode(
            payload,
            SECRET_KEY,
            algorithm="HS256"
        )

        return jsonify({

            "success": True,

            "message": "Login successful",

            "token": token,

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
# TOKEN VERIFICATION
# ============================================================

def verify_token():

    auth_header = request.headers.get(
        "Authorization"
    )

    if not auth_header:

        return None, "Authorization header missing"

    if not auth_header.startswith("Bearer "):

        return None, "Invalid authorization format"

    token = auth_header.split(
        " ",
        1
    )[1]

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        return payload, None

    except jwt.ExpiredSignatureError:

        return None, "Token has expired"

    except jwt.InvalidTokenError:

        return None, "Invalid token"


# ============================================================
# AUTHENTICATION DECORATOR
# ============================================================

def token_required(function):

    @wraps(function)
    def decorated(*args, **kwargs):

        payload, error = verify_token()

        if error:

            return jsonify({
                "success": False,
                "message": error
            }), 401

        request.user = payload

        return function(*args, **kwargs)

    return decorated


# ============================================================
# ROLE-BASED ACCESS
# ============================================================

def roles_required(*allowed_roles):

    def decorator(function):

        @wraps(function)
        def decorated(*args, **kwargs):

            payload, error = verify_token()

            if error:

                return jsonify({
                    "success": False,
                    "message": error
                }), 401

            user_role = payload.get("role")

            if user_role not in allowed_roles:

                return jsonify({

                    "success": False,

                    "message":
                        "Access denied",

                    "required_roles":
                        list(allowed_roles),

                    "your_role":
                        user_role

                }), 403

            request.user = payload

            return function(*args, **kwargs)

        return decorated

    return decorator


# ============================================================
# CURRENT USER
# ============================================================

@auth_api.route(
    "/me",
    methods=["GET"]
)
@token_required
def current_user():

    user_id = request.user.get("user_id")

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

            "user": dict(user)

        })

    finally:

        conn.close()


# ============================================================
# CHECK TOKEN
# ============================================================

@auth_api.route(
    "/verify",
    methods=["GET"]
)
@token_required
def verify_login():

    return jsonify({

        "success": True,

        "message": "Token is valid",

        "user": request.user

    })


# ============================================================
# ADMIN TEST ENDPOINT
# ============================================================

@auth_api.route(
    "/admin-test",
    methods=["GET"]
)
@roles_required("ADMIN")
def admin_test():

    return jsonify({

        "success": True,

        "message":
            "Admin access granted",

        "user":
            request.user

    })


# ============================================================
# DISPATCHER TEST ENDPOINT
# ============================================================

@auth_api.route(
    "/dispatcher-test",
    methods=["GET"]
)
@roles_required(
    "ADMIN",
    "DISPATCHER"
)
def dispatcher_test():

    return jsonify({

        "success": True,

        "message":
            "Dispatcher access granted",

        "user":
            request.user

    })


# ============================================================
# DRIVER TEST ENDPOINT
# ============================================================

@auth_api.route(
    "/driver-test",
    methods=["GET"]
)
@roles_required(
    "ADMIN",
    "DRIVER"
)
def driver_test():

    return jsonify({

        "success": True,

        "message":
            "Driver access granted",

        "user":
            request.user

    })


# ============================================================
# HOSPITAL TEST ENDPOINT
# ============================================================

@auth_api.route(
    "/hospital-test",
    methods=["GET"]
)
@roles_required(
    "ADMIN",
    "HOSPITAL"
)
def hospital_test():

    return jsonify({

        "success": True,

        "message":
            "Hospital access granted",

        "user":
            request.user

    })