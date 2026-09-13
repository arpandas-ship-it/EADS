// ============================================================
// EADS - EMERGENCY PAGE
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    loadEmergencies();

    const form =
        document.getElementById("emergencyForm");

    if (form) {
        form.addEventListener(
            "submit",
            createNewEmergency
        );
    }

});


// ============================================================
// LOAD EMERGENCIES
// ============================================================

async function loadEmergencies() {

    try {

        const data =
            await getEmergencies();

        const emergencies =
            data.emergencies || data;

        const table =
            document.getElementById(
                "emergencyTableBody"
            );

        if (!table) return;

        table.innerHTML = "";

        emergencies.forEach(emergency => {

            const row =
                document.createElement("tr");

            row.innerHTML = `
                <td>${emergency.emergency_code || emergency.id}</td>

                <td>${emergency.caller_name || "-"}</td>

                <td>${emergency.emergency_type || "-"}</td>

                <td>${emergency.priority || "-"}</td>

                <td>${emergency.location || "-"}</td>

                <td>
                    <span class="status">
                        ${emergency.status || "NEW"}
                    </span>
                </td>

                <td>
                    <button
                        onclick="viewEmergency(${emergency.id})">
                        View
                    </button>

                    ${
                        emergency.status === "VERIFIED"
                        ?
                        `<button
                            onclick="dispatchEmergency(${emergency.id})">
                            Dispatch
                        </button>`
                        :
                        ""
                    }
                </td>
            `;

            table.appendChild(row);

        });

    } catch (error) {

        console.error(
            "Unable to load emergencies:",
            error
        );

    }

}


// ============================================================
// CREATE EMERGENCY
// ============================================================

async function createNewEmergency(event) {

    event.preventDefault();

    const data = {

        caller_name:
            document.getElementById(
                "callerName"
            )?.value,

        caller_phone:
            document.getElementById(
                "callerPhone"
            )?.value,

        emergency_type:
            document.getElementById(
                "emergencyType"
            )?.value,

        priority:
            document.getElementById(
                "priority"
            )?.value || "MEDIUM",

        location:
            document.getElementById(
                "location"
            )?.value,

        description:
            document.getElementById(
                "description"
            )?.value,

        latitude:
            parseFloat(
                document.getElementById(
                    "latitude"
                )?.value
            ) || null,

        longitude:
            parseFloat(
                document.getElementById(
                    "longitude"
                )?.value
            ) || null
    };


    try {

        const result =
            await createEmergency(data);

        alert(
            result.message ||
            "Emergency created successfully"
        );

        document
            .getElementById("emergencyForm")
            ?.reset();

        loadEmergencies();

    } catch (error) {

        alert(
            error.message ||
            "Failed to create emergency"
        );

    }

}


// ============================================================
// VIEW EMERGENCY
// ============================================================

async function viewEmergency(id) {

    try {

        const data =
            await getEmergency(id);

        console.log(
            "Emergency:",
            data
        );

        localStorage.setItem(
            "selectedEmergency",
            JSON.stringify(data)
        );

        window.location.href =
            `tracking.html?id=${id}`;

    } catch (error) {

        alert(
            error.message ||
            "Unable to load emergency"
        );

    }

}


// ============================================================
// DISPATCH EMERGENCY
// ============================================================

async function dispatchEmergency(
    emergencyId
) {

    if (
        !confirm(
            "Dispatch the nearest available ambulance?"
        )
    ) {
        return;
    }


    try {

        const result =
            await dispatchAmbulance(
                emergencyId
            );

        alert(
            result.message ||
            "Ambulance dispatched successfully"
        );

        loadEmergencies();

    } catch (error) {

        alert(
            error.message ||
            "Dispatch failed"
        );

    }

}


// ============================================================
// VERIFY EMERGENCY
// ============================================================

async function verifyEmergency(
    emergencyId
) {

    try {

        const result =
            await updateEmergencyStatus(
                emergencyId,
                "VERIFIED"
            );

        alert(
            result.message ||
            "Emergency verified"
        );

        loadEmergencies();

    } catch (error) {

        alert(
            error.message ||
            "Verification failed"
        );

    }

}


// ============================================================
// CANCEL EMERGENCY
// ============================================================

async function cancelEmergency(
    emergencyId
) {

    if (
        !confirm(
            "Cancel this emergency?"
        )
    ) {
        return;
    }


    try {

        const result =
            await updateEmergencyStatus(
                emergencyId,
                "CANCELLED"
            );

        alert(
            result.message ||
            "Emergency cancelled"
        );

        loadEmergencies();

    } catch (error) {

        alert(
            error.message ||
            "Cancellation failed"
        );

    }

}


// ============================================================
// AUTO REFRESH
// ============================================================

setInterval(
    loadEmergencies,
    10000
);