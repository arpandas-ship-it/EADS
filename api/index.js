const state = {
    emergencies: [],
    ambulances: [
        { id: 1, ambulance_number: "AMB-001", driver_name: "Rahul Sharma", status: "AVAILABLE", current_location: "City Center" },
        { id: 2, ambulance_number: "AMB-002", driver_name: "Amit Das", status: "AVAILABLE", current_location: "North Zone" },
        { id: 3, ambulance_number: "AMB-003", driver_name: "Rohit Singh", status: "EN_ROUTE", current_location: "East Zone" }
    ],
    hospitals: [
        { id: 1, name: "City General Hospital", location: "Main Road", emergency_available: "Yes", available_beds: 25 },
        { id: 2, name: "Life Care Hospital", location: "North Avenue", emergency_available: "Yes", available_beds: 18 }
    ],
    users: [
        { id: 1, name: "Administrator", email: "admin@eads.com", role: "ADMINISTRATOR", status: "Active" }
    ]
};

function send(res, status, payload) {
    res.statusCode = status;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(payload));
}

function readBody(req) {
    return new Promise((resolve, reject) => {
        let body = "";
        req.on("data", chunk => { body += chunk; });
        req.on("end", () => {
            if (!body) return resolve({});
            try {
                resolve(JSON.parse(body));
            } catch (error) {
                reject(new Error("Request body must be valid JSON"));
            }
        });
        req.on("error", reject);
    });
}

function nextId(items) {
    return items.reduce((highest, item) => Math.max(highest, Number(item.id) || 0), 0) + 1;
}

function resourceFor(path) {
    const match = path.match(/^\/(emergencies|ambulances|hospitals|users)(?:\/(\d+))?$/);
    return match ? { name: match[1], id: match[2] ? Number(match[2]) : null } : null;
}

async function handler(req, res) {
    const requestUrl = typeof req.url === "string" ? req.url : "/api/health";
    const url = new URL(requestUrl, "http://localhost");
    let path = url.pathname.replace(/^\/api/, "") || "/";

    if (path === "/index.js") {
        path = "/";
    }

    if (req.method === "OPTIONS") {
        res.statusCode = 204;
        return res.end();
    }

    if (req.method === "GET" && path === "/health") {
        return send(res, 200, { status: "OK", message: "EADS API is operational" });
    }

    if (req.method === "GET" && path === "/reports/summary") {
        const active = state.emergencies.filter(item => !["COMPLETED", "CANCELLED"].includes(item.status)).length;
        return send(res, 200, {
            success: true,
            data: {
                total_emergencies: state.emergencies.length,
                active_emergencies: active,
                available_ambulances: state.ambulances.filter(item => item.status === "AVAILABLE").length
            }
        });
    }

    if (req.method === "GET" && path === "/tracking/active") {
        return send(res, 200, { success: true, data: state.ambulances.filter(item => item.status !== "AVAILABLE") });
    }

    const resource = resourceFor(path);
    if (resource) {
        const items = state[resource.name];

        if (req.method === "GET" && resource.id === null) {
            return send(res, 200, { success: true, data: items });
        }

        if (req.method === "GET" && resource.id !== null) {
            const item = items.find(entry => entry.id === resource.id);
            return item ? send(res, 200, { success: true, data: item }) : send(res, 404, { success: false, message: "Record not found" });
        }

        if (req.method === "POST" && resource.id === null) {
            const body = await readBody(req);
            const item = { ...body, id: nextId(items) };
            if (resource.name === "emergencies") item.status = item.status || "NEW";
            if (resource.name === "ambulances") item.status = item.status || "AVAILABLE";
            if (resource.name === "users") item.status = item.status || "Active";
            items.unshift(item);
            return send(res, 201, { success: true, message: "Record created successfully", data: item, id: item.id });
        }

        if (req.method === "PUT" && resource.id !== null) {
            const index = items.findIndex(entry => entry.id === resource.id);
            if (index < 0) return send(res, 404, { success: false, message: "Record not found" });
            const body = await readBody(req);
            items[index] = { ...items[index], ...body, id: resource.id };
            return send(res, 200, { success: true, data: items[index] });
        }
    }

    return send(res, 404, { success: false, message: "API endpoint not found" });
}

module.exports = handler;
module.exports.default = handler;
