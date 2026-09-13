// ============================================================
// EADS - FRONTEND API CONNECTION
// ============================================================

const API_BASE_URL = "http://127.0.0.1:5000/api";


// ============================================================
// GENERIC API REQUEST
// ============================================================

async function apiRequest(endpoint, options = {}) {

    try {

        const response = await fetch(
            `${API_BASE_URL}${endpoint}`,
            {
                ...options,

                headers: {
                    "Content-Type": "application/json",
                    ...(options.headers || {})
                }
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.message ||
                data.error ||
                "API request failed"
            );
        }

        return data;

    } catch (error) {

        console.error(
            "API Error:",
            error
        );

        throw error;
    }
}


// ============================================================
// DASHBOARD
// ============================================================

async function getDashboard() {

    return await apiRequest(
        "/dashboard"
    );
}


async function getDashboardEmergencies() {

    return await apiRequest(
        "/dashboard/emergencies"
    );
}


async function getCriticalAlerts() {

    return await apiRequest(
        "/dashboard/critical-alerts"
    );
}


async function getAvailableAmbulances() {

    return await apiRequest(
        "/dashboard/available-ambulances"
    );
}


// ============================================================
// EMERGENCIES
// ============================================================

async function getEmergencies() {

    return await apiRequest(
        "/emergencies"
    );
}


async function getEmergency(id) {

    return await apiRequest(
        `/emergencies/${id}`
    );
}


async function createEmergency(emergencyData) {

    return await apiRequest(
        "/emergencies",
        {
            method: "POST",

            body: JSON.stringify(
                emergencyData
            )
        }
    );
}


async function updateEmergency(
    id,
    emergencyData
) {

    return await apiRequest(
        `/emergencies/${id}`,
        {
            method: "PUT",

            body: JSON.stringify(
                emergencyData
            )
        }
    );
}


// ============================================================
// DISPATCH
// ============================================================

async function dispatchAmbulance(
    emergencyId,
    ambulanceId = null
) {

    const body = {};

    if (ambulanceId) {

        body.ambulance_id =
            ambulanceId;
    }

    return await apiRequest(
        `/dispatch/emergency/${emergencyId}`,
        {
            method: "POST",

            body: JSON.stringify(body)
        }
    );
}


// ============================================================
// TRACKING
// ============================================================

async function getEmergencyTracking(
    emergencyId
) {

    return await apiRequest(
        `/tracking/emergency/${emergencyId}`
    );
}


async function getActiveTracking() {

    return await apiRequest(
        "/tracking/active"
    );
}


async function updateAmbulanceLocation(
    ambulanceId,
    latitude,
    longitude
) {

    return await apiRequest(
        `/tracking/ambulance/${ambulanceId}/location`,
        {
            method: "PUT",

            body: JSON.stringify({

                latitude:
                    latitude,

                longitude:
                    longitude
            })
        }
    );
}


async function updateEmergencyStatus(
    emergencyId,
    status
) {

    return await apiRequest(
        `/tracking/emergency/${emergencyId}/status`,
        {
            method: "PUT",

            body: JSON.stringify({

                status:
                    status
            })
        }
    );
}


// ============================================================
// AMBULANCES
// ============================================================

async function getAmbulances() {

    return await apiRequest(
        "/ambulances"
    );
}


async function getAmbulance(id) {

    return await apiRequest(
        `/ambulances/${id}`
    );
}


// ============================================================
// HOSPITALS
// ============================================================

async function getHospitals() {

    return await apiRequest(
        "/hospitals"
    );
}


async function getEmergencyHospitals(
    emergencyId
) {

    return await apiRequest(
        `/hospital-integration/emergency/${emergencyId}/hospitals`
    );
}


async function assignHospital(
    emergencyId,
    hospitalId
) {

    return await apiRequest(
        `/hospital-integration/emergency/${emergencyId}/assign`,
        {
            method: "PUT",

            body: JSON.stringify({

                hospital_id:
                    hospitalId
            })
        }
    );
}


// ============================================================
// USERS
// ============================================================

async function getUsers() {

    return await apiRequest(
        "/users"
    );
}


async function getUser(id) {

    return await apiRequest(
        `/users/${id}`
    );
}


// ============================================================
// NOTIFICATIONS
// ============================================================

async function getNotifications() {

    return await apiRequest(
        "/notifications"
    );
}


async function getUnreadNotifications() {

    return await apiRequest(
        "/notifications/unread"
    );
}


async function markNotificationRead(
    notificationId
) {

    return await apiRequest(
        `/notifications/${notificationId}/read`,
        {
            method: "PUT"
        }
    );
}


async function markAllNotificationsRead() {

    return await apiRequest(
        "/notifications/read-all",
        {
            method: "PUT"
        }
    );
}


// ============================================================
// REPORTS
// ============================================================

async function getReportSummary() {

    return await apiRequest(
        "/reports/summary"
    );
}


async function getEmergencyStatusReport() {

    return await apiRequest(
        "/reports/emergency-status"
    );
}


async function getPriorityReport() {

    return await apiRequest(
        "/reports/priority"
    );
}


async function getEmergencyTypeReport() {

    return await apiRequest(
        "/reports/types"
    );
}


async function getResponseTimeReport() {

    return await apiRequest(
        "/reports/response-time"
    );
}


async function getAmbulanceReport() {

    return await apiRequest(
        "/reports/ambulances"
    );
}


async function getHospitalReport() {

    return await apiRequest(
        "/reports/hospitals"
    );
}


async function getCriticalCases() {

    return await apiRequest(
        "/reports/critical"
    );
}


async function getSystemHealth() {

    return await apiRequest(
        "/reports/system-health"
    );
}


// ============================================================
// LOGIN
// ============================================================

async function loginUser(
    email,
    password
) {

    return await apiRequest(
        "/auth/login",
        {
            method: "POST",

            body: JSON.stringify({

                email: email,

                password: password
            })
        }
    );
}


// ============================================================
// LOGOUT
// ============================================================

function logoutUser() {

    localStorage.removeItem(
        "token"
    );

    localStorage.removeItem(
        "user"
    );

    window.location.href =
        "login.html";
}


// ============================================================
// SAVE LOGIN
// ============================================================

function saveLoginData(data) {

    if (data.token) {

        localStorage.setItem(
            "token",
            data.token
        );
    }

    if (data.user) {

        localStorage.setItem(
            "user",
            JSON.stringify(
                data.user
            )
        );
    }
}


// ============================================================
// GET CURRENT USER
// ============================================================

function getCurrentUser() {

    const user =
        localStorage.getItem(
            "user"
        );

    if (!user) {

        return null;
    }

    try {

        return JSON.parse(
            user
        );

    } catch {

        return null;
    }
}


// ============================================================
// TOKEN
// ============================================================

function getToken() {

    return localStorage.getItem(
        "token"
    );
}


// ============================================================
// AUTO REFRESH DASHBOARD
// ============================================================

async function refreshDashboard() {

    try {

        const data =
            await getDashboard();

        console.log(
            "Dashboard updated:",
            data
        );

        return data;

    } catch (error) {

        console.error(
            "Dashboard refresh failed:",
            error
        );
    }
}


// Refresh every 10 seconds

setInterval(
    refreshDashboard,
    10000
);