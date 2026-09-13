# emergency_validation.py

# ============================================================
# EMERGENCY STATUS VALIDATION
# Emergency Ambulance Dispatch System
# ============================================================


# ------------------------------------------------------------
# VALID EMERGENCY STATUSES
# ------------------------------------------------------------

VALID_STATUSES = [
    "NEW",
    "VERIFIED",
    "DISPATCHED",
    "EN_ROUTE",
    "ON_SCENE",
    "TRANSPORTING",
    "COMPLETED",
    "CANCELLED"
]


# ------------------------------------------------------------
# VALID STATUS TRANSITIONS
# ------------------------------------------------------------

STATUS_TRANSITIONS = {

    "NEW": [
        "VERIFIED",
        "CANCELLED"
    ],

    "VERIFIED": [
        "DISPATCHED",
        "CANCELLED"
    ],

    "DISPATCHED": [
        "EN_ROUTE",
        "CANCELLED"
    ],

    "EN_ROUTE": [
        "ON_SCENE",
        "CANCELLED"
    ],

    "ON_SCENE": [
        "TRANSPORTING",
        "CANCELLED"
    ],

    "TRANSPORTING": [
        "COMPLETED",
        "CANCELLED"
    ],

    "COMPLETED": [],

    "CANCELLED": []
}


# ------------------------------------------------------------
# CHECK WHETHER STATUS IS VALID
# ------------------------------------------------------------

def is_valid_status(status):

    if not status:
        return False

    return status.upper() in VALID_STATUSES


# ------------------------------------------------------------
# CHECK WHETHER STATUS TRANSITION IS VALID
# ------------------------------------------------------------

def is_valid_transition(old_status, new_status):

    if not old_status or not new_status:
        return False

    old_status = old_status.upper()
    new_status = new_status.upper()

    # Check both statuses
    if old_status not in VALID_STATUSES:
        return False

    if new_status not in VALID_STATUSES:
        return False

    # Same status is not considered a transition
    if old_status == new_status:
        return False

    # Check allowed transition
    return new_status in STATUS_TRANSITIONS.get(
        old_status,
        []
    )


# ------------------------------------------------------------
# GET NEXT POSSIBLE STATUSES
# ------------------------------------------------------------

def get_next_statuses(current_status):

    if not current_status:
        return []

    current_status = current_status.upper()

    return STATUS_TRANSITIONS.get(
        current_status,
        []
    )


# ------------------------------------------------------------
# GET STATUS INFORMATION
# ------------------------------------------------------------

def get_status_info(status):

    status = status.upper()

    information = {

        "NEW": {
            "label": "New Emergency",
            "description": "Emergency request has been received.",
            "next": ["VERIFIED", "CANCELLED"]
        },

        "VERIFIED": {
            "label": "Verified",
            "description": "Emergency information has been verified.",
            "next": ["DISPATCHED", "CANCELLED"]
        },

        "DISPATCHED": {
            "label": "Ambulance Dispatched",
            "description": "An ambulance has been assigned.",
            "next": ["EN_ROUTE", "CANCELLED"]
        },

        "EN_ROUTE": {
            "label": "En Route",
            "description": "Ambulance is travelling to the incident.",
            "next": ["ON_SCENE", "CANCELLED"]
        },

        "ON_SCENE": {
            "label": "On Scene",
            "description": "Ambulance has reached the incident location.",
            "next": ["TRANSPORTING", "CANCELLED"]
        },

        "TRANSPORTING": {
            "label": "Transporting",
            "description": "Patient is being transported to the hospital.",
            "next": ["COMPLETED", "CANCELLED"]
        },

        "COMPLETED": {
            "label": "Completed",
            "description": "Emergency case has been completed.",
            "next": []
        },

        "CANCELLED": {
            "label": "Cancelled",
            "description": "Emergency case has been cancelled.",
            "next": []
        }
    }

    return information.get(
        status,
        None
    )


# ------------------------------------------------------------
# VALIDATE EMERGENCY DATA
# ------------------------------------------------------------

def validate_emergency_data(data):

    errors = []

    if not data:
        errors.append(
            "Emergency data is required."
        )
        return errors

    # Caller name
    if not data.get("caller_name"):
        errors.append(
            "Caller name is required."
        )

    # Caller phone
    if not data.get("caller_phone"):
        errors.append(
            "Caller phone is required."
        )

    # Emergency type
    if not data.get("emergency_type"):
        errors.append(
            "Emergency type is required."
        )

    # Location
    if not data.get("location"):
        errors.append(
            "Emergency location is required."
        )

    # Priority
    priority = data.get(
        "priority",
        "MEDIUM"
    ).upper()

    valid_priorities = [
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ]

    if priority not in valid_priorities:
        errors.append(
            "Priority must be LOW, MEDIUM, HIGH or CRITICAL."
        )

    return errors


# ------------------------------------------------------------
# PRIORITY VALIDATION
# ------------------------------------------------------------

def is_valid_priority(priority):

    if not priority:
        return False

    return priority.upper() in [
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ]


# ------------------------------------------------------------
# GET PRIORITY LEVEL
# ------------------------------------------------------------

def get_priority_level(priority):

    priority_levels = {

        "LOW": 1,

        "MEDIUM": 2,

        "HIGH": 3,

        "CRITICAL": 4
    }

    return priority_levels.get(
        priority.upper(),
        0
    )


# ------------------------------------------------------------
# CHECK WHETHER EMERGENCY IS ACTIVE
# ------------------------------------------------------------

def is_active_emergency(status):

    if not status:
        return False

    return status.upper() not in [
        "COMPLETED",
        "CANCELLED"
    ]


# ------------------------------------------------------------
# CHECK WHETHER EMERGENCY CAN BE DISPATCHED
# ------------------------------------------------------------

def can_dispatch(status):

    if not status:
        return False

    return status.upper() == "VERIFIED"


# ------------------------------------------------------------
# CHECK WHETHER EMERGENCY CAN BE COMPLETED
# ------------------------------------------------------------

def can_complete(status):

    if not status:
        return False

    return status.upper() == "TRANSPORTING"


# ------------------------------------------------------------
# CHECK WHETHER EMERGENCY CAN BE CANCELLED
# ------------------------------------------------------------

def can_cancel(status):

    if not status:
        return False

    return status.upper() not in [
        "COMPLETED",
        "CANCELLED"
    ]