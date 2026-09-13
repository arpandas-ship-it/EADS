const express = require("express");
const cors = require("cors");

const app = express();

const PORT = 5000;

// Database
require("./database");

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
const emergencyRoutes = require("./routes/emergencyRoutes");
const ambulanceRoutes = require("./routes/ambulanceRoutes");
const hospitalRoutes = require("./routes/hospitalRoutes");
const userRoutes = require("./routes/userRoutes");
const trackingRoutes = require("./routes/trackingRoutes");
const reportRoutes = require("./routes/reportRoutes");

app.use("/api/emergencies", emergencyRoutes);
app.use("/api/ambulances", ambulanceRoutes);
app.use("/api/hospitals", hospitalRoutes);
app.use("/api/users", userRoutes);
app.use("/api/tracking", trackingRoutes);
app.use("/api/reports", reportRoutes);

// Home
app.get("/", (req, res) => {
    res.json({
        system: "Emergency Ambulance Dispatch System",
        status: "Backend Running",
        version: "1.0"
    });
});

// Health check
app.get("/api/health", (req, res) => {
    res.json({
        status: "OK",
        message: "EADS backend is operational"
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        success: false,
        message: "API endpoint not found"
    });
});

// Error handler
app.use((err, req, res, next) => {
    console.error(err);

    res.status(500).json({
        success: false,
        message: "Internal server error"
    });
});

app.listen(PORT, () => {
    console.log("--------------------------------------");
    console.log(" EADS BACKEND SERVER");
    console.log("--------------------------------------");
    console.log(`Server running on http://localhost:${PORT}`);
    console.log("API ready.");
});