const express = require("express");
const router = express.Router();
const db = require("../database");

// GET ALL EMERGENCIES
router.get("/", (req, res) => {

    const sql = `
        SELECT
            e.*,
            a.ambulance_number,
            h.name AS hospital_name
        FROM emergencies e
        LEFT JOIN ambulances a
            ON e.ambulance_id = a.id
        LEFT JOIN hospitals h
            ON e.hospital_id = h.id
        ORDER BY e.id DESC
    `;

    db.all(sql, [], (err, rows) => {

        if (err) {
            return res.status(500).json({
                success: false,
                message: err.message
            });
        }

        res.json({
            success: true,
            data: rows
        });
    });
});


// GET SINGLE EMERGENCY
router.get("/:id", (req, res) => {

    db.get(
        `SELECT * FROM emergencies WHERE id = ?`,
        [req.params.id],
        (err, row) => {

            if (err) {
                return res.status(500).json({
                    success: false,
                    message: err.message
                });
            }

            if (!row) {
                return res.status(404).json({
                    success: false,
                    message: "Emergency not found"
                });
            }

            res.json({
                success: true,
                data: row
            });
        }
    );
});


// CREATE EMERGENCY
router.post("/", (req, res) => {

    const {
        caller_name,
        emergency_type,
        priority,
        location,
        description,
        patient_name,
        patient_age,
        condition
    } = req.body;

    if (
        !caller_name ||
        !emergency_type ||
        !priority ||
        !location
    ) {
        return res.status(400).json({
            success: false,
            message: "Required emergency information is missing"
        });
    }

    const emergencyId =
        "E-" +
        Date.now().toString().slice(-6);

    const sql = `
        INSERT INTO emergencies
        (
            emergency_id,
            caller_name,
            emergency_type,
            priority,
            location,
            description,
            patient_name,
            patient_age,
            condition
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;

    db.run(
        sql,
        [
            emergencyId,
            caller_name,
            emergency_type,
            priority,
            location,
            description || "",
            patient_name || "",
            patient_age || null,
            condition || ""
        ],
        function(err) {

            if (err) {
                return res.status(500).json({
                    success: false,
                    message: err.message
                });
            }

            res.status(201).json({
                success: true,
                message: "Emergency created successfully",
                emergency_id: emergencyId,
                id: this.lastID
            });
        }
    );
});


// UPDATE EMERGENCY STATUS
router.put("/:id/status", (req, res) => {

    const { status } = req.body;

    const allowedStatuses = [
        "Pending",
        "Dispatched",
        "En Route",
        "On Scene",
        "Transporting",
        "Completed"
    ];

    if (!allowedStatuses.includes(status)) {
        return res.status(400).json({
            success: false,
            message: "Invalid emergency status"
        });
    }

    db.run(
        `UPDATE emergencies SET status = ? WHERE id = ?`,
        [status, req.params.id],
        function(err) {

            if (err) {
                return res.status(500).json({
                    success: false,
                    message: err.message
                });
            }

            if (this.changes === 0) {
                return res.status(404).json({
                    success: false,
                    message: "Emergency not found"
                });
            }

            res.json({
                success: true,
                message: "Emergency status updated"
            });
        }
    );
});


// DELETE EMERGENCY
router.delete("/:id", (req, res) => {

    db.run(
        `DELETE FROM emergencies WHERE id = ?`,
        [req.params.id],
        function(err) {

            if (err) {
                return res.status(500).json({
                    success: false,
                    message: err.message
                });
            }

            res.json({
                success: true,
                message: "Emergency deleted"
            });
        }
    );
});


module.exports = router;