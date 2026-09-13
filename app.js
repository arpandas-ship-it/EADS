const API = "/api";

/* =========================================================
   GLOBAL INITIALIZATION
========================================================= */

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", () => {
        setupNavigation();
        setupEmergencyPage();
        setupEmergencyForm();
        setupDashboard();
    });
}


/* =========================================================
   NAVIGATION
========================================================= */

function setupNavigation() {

    document.querySelectorAll(".nav-item").forEach(link => {

        link.addEventListener("click", function (e) {

            const target = this.getAttribute("href");

            if (!target || target === "#") {
                e.preventDefault();
                return;
            }

            window.location.href = target;
        });

    });
}


/* =========================================================
   EMERGENCY PAGE
========================================================= */

function setupEmergencyPage() {

    const tableBody =
        document.getElementById("emergencyTableBody");

    if (!tableBody) return;

    loadEmergencies();

    const search =
        document.getElementById("emergencySearch");

    const status =
        document.getElementById("emergencyStatus");

    const priority =
        document.getElementById("emergencyPriority");

    if (search) {
        search.addEventListener("input", filterEmergencies);
    }

    if (status) {
        status.addEventListener("change", filterEmergencies);
    }

    if (priority) {
        priority.addEventListener("change", filterEmergencies);
    }

    loadDispatchData();
}


/* =========================================================
   LOAD EMERGENCIES
========================================================= */

async function loadEmergencies() {

    try {

        const response =
            await fetch(`${API}/emergencies`);

        const result =
            await response.json();

        if (!result.success) {
            throw new Error(result.message);
        }

        const emergencies =
            Array.isArray(result.emergencies)
                ? result.emergencies
                : Array.isArray(result.data)
                    ? result.data
                    : [];

        renderEmergencies(emergencies);
        updateEmergencyStatistics(emergencies);

    } catch (error) {

        console.error("Emergency loading error:", error);

        const tableBody =
            document.getElementById("emergencyTableBody");

        if (tableBody) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;padding:30px;">
                        Unable to connect to backend server.
                    </td>
                </tr>
            `;
        }
    }
}


/* =========================================================
   RENDER EMERGENCY TABLE
========================================================= */

function renderEmergencies(emergencies) {

    const tableBody =
        document.getElementById("emergencyTableBody");

    if (!tableBody) return;

    tableBody.innerHTML = "";

    if (emergencies.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center;padding:30px;">
                    No emergency records found.
                </td>
            </tr>
        `;

        return;
    }

    emergencies.forEach(emergency => {

        const emergencyId = emergency.id ?? emergency.emergency_id ?? emergency.emergencyId;
        const status = uiStatusLabel(emergency.status);
        const priority = uiPriorityLabel(emergency.priority);

        const row =
            document.createElement("tr");

        row.dataset.search =
            `${emergencyId}
             ${emergency.emergency_type || ""}
             ${emergency.location || ""}`.toLowerCase();

        row.dataset.status =
            normalizeStatus(emergency.status);

        row.dataset.priority =
            normalizeStatus(emergency.priority);

        row.innerHTML = `

            <td>
                <strong>${escapeHTML(emergency.emergency_code || emergencyId)}</strong>
            </td>

            <td>
                ${escapeHTML(emergency.emergency_type || "-")}
            </td>

            <td>
                ${escapeHTML(emergency.location || "-")}
            </td>

            <td>
                <span class="priority-badge ${getPriorityClass(priority)}">
                    ${escapeHTML(priority || "-")}
                </span>
            </td>

            <td>
                ${emergency.ambulance_number
                    ? escapeHTML(emergency.ambulance_number)
                    : "Not Assigned"}
            </td>

            <td>
                <select
                    class="status-select"
                    onchange="changeEmergencyStatus(${emergencyId}, this.value)"
                >
                    ${createStatusOptions(emergency.status)}
                </select>
            </td>

            <td>
                <button
                    class="btn btn-secondary"
                    onclick="viewEmergency(${emergencyId})"
                >
                    View
                </button>
            </td>
        `;

        tableBody.appendChild(row);
    });
}


/* =========================================================
   STATUS OPTIONS
========================================================= */

function createStatusOptions(currentStatus) {

    const apiStatuses = [
        ["RECEIVED", "Received"],
        ["VERIFIED", "Verified"],
        ["DISPATCHED", "Dispatched"],
        ["EN_ROUTE", "En Route"],
        ["ON_SCENE", "On Scene"],
        ["TRANSPORTING", "Transporting"],
        ["COMPLETED", "Completed"],
        ["CANCELLED", "Cancelled"]
    ];

    return apiStatuses.map(([apiValue, label]) => {

        return `
            <option
                value="${apiValue}"
                ${normalizeStatus(currentStatus) === apiValue ? "selected" : ""}
            >
                ${label}
            </option>
        `;

    }).join("");
}


/* =========================================================
   UPDATE EMERGENCY STATUS
========================================================= */

async function changeEmergencyStatus(id, status) {

    try {

        const apiStatus =
            apiStatusValue(status);

        const response = await fetch(
            `${API}/emergencies/${id}/status`,
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    status: apiStatus
                })
            }
        );

        const result =
            await response.json();

        if (!result.success) {
            throw new Error(result.message);
        }

        await loadEmergencies();

    } catch (error) {

        console.error(error);

        alert("Unable to update emergency status.");
    }
}


/* =========================================================
   FILTER EMERGENCIES
========================================================= */

function filterEmergencies() {

    const search =
        document.getElementById("emergencySearch")
        ?.value
        .toLowerCase() || "";

    const status =
        document.getElementById("emergencyStatus")
        ?.value || "";

    const priority =
        document.getElementById("emergencyPriority")
        ?.value || "";

    document
        .querySelectorAll("#emergencyTableBody tr")
        .forEach(row => {

            const text =
                row.dataset.search || "";

            const rowStatus =
                row.dataset.status || "";

            const rowPriority =
                row.dataset.priority || "";

            const searchMatch =
                text.includes(search);

            const statusMatch =
                !status ||
                rowStatus === status;

            const priorityMatch =
                !priority ||
                rowPriority === priority;

            row.style.display =
                searchMatch &&
                statusMatch &&
                priorityMatch
                    ? ""
                    : "none";
        });
}


/* =========================================================
   EMERGENCY STATISTICS
========================================================= */

function updateEmergencyStatistics(emergencies) {

    const active =
        emergencies.filter(e =>
            !["COMPLETED", "CANCELLED"].includes(normalizeStatus(e.status))
        ).length;

    const critical =
        emergencies.filter(e =>
            normalizeStatus(e.priority) === "CRITICAL"
        ).length;

    const pending =
        emergencies.filter(e =>
            normalizeStatus(e.status) === "RECEIVED"
        ).length;

    const completed =
        emergencies.filter(e =>
            normalizeStatus(e.status) === "COMPLETED"
        ).length;

    setText("activeEmergencyCount", active);
    setText("criticalEmergencyCount", critical);
    setText("pendingEmergencyCount", pending);
    setText("completedEmergencyCount", completed);

    setText("criticalCount",
        emergencies.filter(e => normalizeStatus(e.priority) === "CRITICAL").length);

    setText("highCount",
        emergencies.filter(e => normalizeStatus(e.priority) === "HIGH").length);

    setText("mediumCount",
        emergencies.filter(e => normalizeStatus(e.priority) === "MEDIUM").length);

    setText("lowCount",
        emergencies.filter(e => normalizeStatus(e.priority) === "LOW").length);
}


/* =========================================================
   DISPATCH DATA
========================================================= */

async function loadDispatchData() {

    try {

        const response =
            await fetch(`${API}/ambulances`);

        const result =
            await response.json();

        if (!result.success) return;

        const ambulances =
            Array.isArray(result.ambulances)
                ? result.ambulances
                : Array.isArray(result.data)
                    ? result.data
                    : [];

        const ambulanceSelect =
            document.getElementById("dispatchAmbulance");

        if (!ambulanceSelect) return;

        ambulanceSelect.innerHTML =
            `<option value="">Select Ambulance</option>`;

        ambulances.forEach(ambulance => {

            const option =
                document.createElement("option");

            option.value =
                ambulance.id;

            option.textContent =
                `${ambulance.ambulance_number} - ${uiStatusLabel(ambulance.status)}`;

            ambulanceSelect.appendChild(option);
        });

        const available =
            ambulances.filter(
                a => normalizeStatus(a.status) === "AVAILABLE"
            ).length;

        const dispatched =
            ambulances.filter(
                a => normalizeStatus(a.status) === "DISPATCHED"
            ).length;

        const enRoute =
            ambulances.filter(
                a => normalizeStatus(a.status) === "EN_ROUTE"
            ).length;

        setText(
            "availableAmbulanceCount",
            available
        );

        setText(
            "dispatchedAmbulanceCount",
            dispatched
        );

        setText(
            "enRouteAmbulanceCount",
            enRoute
        );

    } catch (error) {

        console.error(
            "Dispatch data error:",
            error
        );
    }
}


/* =========================================================
   EMERGENCY FORM
========================================================= */

function setupEmergencyForm() {

    const form =
        document.getElementById("emergencyForm");

    if (!form) return;

    form.addEventListener("submit", async function(e) {

        e.preventDefault();

        const data = {

            caller_name:
                getValue("callerName"),

            emergency_type:
                getValue("emergencyType"),

            priority:
                getValue("priority"),

            location:
                getValue("location"),

            description:
                getValue("description"),

            patient_name:
                getValue("patientName"),

            patient_age:
                getValue("patientAge")
                    ? Number(getValue("patientAge"))
                    : null,

            condition:
                getValue("condition")
        };

        if (
            !data.caller_name ||
            !data.emergency_type ||
            !data.priority ||
            !data.location
        ) {

            alert(
                "Please complete all required fields."
            );

            return;
        }

        try {

            const response =
                await fetch(
                    `${API}/emergencies`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(data)
                    }
                );

            const result =
                await response.json();

            if (!result.success) {
                throw new Error(result.message);
            }

            const emergencyId =
                result.emergency?.id ?? result.emergency_id ?? "";

            alert(
                `Emergency ${emergencyId || "created"} created successfully.`
            );

            form.reset();

            window.location.href =
                "emergency.html";

        } catch (error) {

            console.error(error);

            alert(
                "Unable to create emergency. Make sure the backend server is running."
            );
        }

    });
}


/* =========================================================
   DASHBOARD
========================================================= */

async function setupDashboard() {

    const totalElement =
        document.getElementById("totalEmergencies");

    if (!totalElement) return;

    try {

        const response =
            await fetch(
                `${API}/reports/summary`
            );

        const result =
            await response.json();

        if (!result.success) return;

        const summary =
            result.summary || result.data || {};

        setText(
            "totalEmergencies",
            summary.total_emergencies ?? summary.totalEmergencies ?? 0
        );

        setText(
            "activeEmergencies",
            summary.active_emergencies ?? summary.activeEmergencies ?? 0
        );

        setText(
            "availableAmbulances",
            summary.available_ambulances ?? summary.availableAmbulances ?? 0
        );

    } catch (error) {

        console.error(
            "Dashboard API error:",
            error
        );
    }
}


/* =========================================================
   VIEW EMERGENCY
========================================================= */

async function viewEmergency(id) {

    try {

        const response =
            await fetch(
                `${API}/emergencies/${id}`
            );

        const result =
            await response.json();

        if (!result.success) {
            throw new Error(result.message);
        }

        const emergency =
            result.emergency || result.data || {};

        alert(
`Emergency ID: ${emergency.id ?? emergency.emergency_id ?? id}

Caller: ${emergency.caller_name || "Not provided"}

Type: ${emergency.emergency_type || "Not provided"}

Priority: ${uiPriorityLabel(emergency.priority)}

Location: ${emergency.location || "Not provided"}

Patient: ${emergency.patient_name || "Not provided"}

Age: ${emergency.patient_age || "Not provided"}

Condition: ${emergency.condition || "Not provided"}

Status: ${uiStatusLabel(emergency.status)}`
        );

    } catch (error) {

        console.error(error);

        alert(
            "Unable to load emergency details."
        );
    }
}


/* =========================================================
   UTILITY FUNCTIONS
========================================================= */

function getValue(id) {

    const element =
        document.getElementById(id);

    return element
        ? element.value.trim()
        : "";
}


function setText(id, value) {

    const element =
        document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function getPriorityClass(priority) {

    switch (normalizeStatus(priority)) {

        case "CRITICAL":
            return "priority-critical";

        case "HIGH":
            return "priority-high";

        case "MEDIUM":
            return "priority-medium";

        case "LOW":
            return "priority-low";

        default:
            return "";
    }
}

function normalizeStatus(value) {
    return String(value ?? "").trim().toUpperCase();
}

function uiStatusLabel(value) {
    const status = normalizeStatus(value);
    const labels = {
        RECEIVED: "Received",
        VERIFIED: "Verified",
        DISPATCHED: "Dispatched",
        EN_ROUTE: "En Route",
        ON_SCENE: "On Scene",
        TRANSPORTING: "Transporting",
        COMPLETED: "Completed",
        CANCELLED: "Cancelled",
        PENDING: "Pending"
    };

    return labels[status] || String(value ?? "-");
}

function uiPriorityLabel(value) {
    const priority = normalizeStatus(value);
    const labels = {
        CRITICAL: "Critical",
        HIGH: "High",
        MEDIUM: "Medium",
        LOW: "Low"
    };

    return labels[priority] || String(value ?? "-");
}

function apiStatusValue(value) {
    const status = String(value ?? "").trim();
    const map = {
        Pending: "RECEIVED",
        Received: "RECEIVED",
        Verified: "VERIFIED",
        Dispatched: "DISPATCHED",
        "En Route": "EN_ROUTE",
        "On Scene": "ON_SCENE",
        Transporting: "TRANSPORTING",
        Completed: "COMPLETED",
        Cancelled: "CANCELLED",
        New: "RECEIVED"
    };

    return map[status] || normalizeStatus(status);
}


function escapeHTML(value) {

    if (value === null ||
        value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}