const express = require("express");
const router = express.Router();
const db = require("../database");


// GET CURRENT AMBULANCE LOCATIONS
router.get("/", (req, res) => {

    db.all(
        `
        SELECT
            a.id,
            a.ambulance_number,
            a.status,
            a.location,
            a.latitude,
            a.longitude,
            t.recorded_at
        FROM ambulances a
        LEFT JOIN tracking t
        ON t.id = (
            SELECT MAX(id)
            FROM tracking
            WHERE ambulance_id = a.id
        )
        `,
        [],
        (err, rows) => {

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
        }
    );
});


// UPDATE AMBULANCE LOCATION
router.post("/", (req, res) => {

    const {
        ambulance_id,
        emergency_id,
        latitude,
        longitude,
        status
    } = req.body;

    if (!ambulance_id || latitude === undefined || longitude === undefined) {
        return res.status(400).json({
            success: false,
            message: "Ambulance and location are required"
        });
    }

    db.run(
        `
        INSERT INTO tracking
        (
            ambulance_id,
            emergency_id,
            latitude,
            longitude,
            status
        )
        VALUES (?, ?, ?, ?, ?)
        `,
        [
            ambulance_id,
            emergency_id || null,
            latitude,
            longitude,
            status || "En Route"
        ],
        function(err) {

            if (err) {
                return res.status(500).json({
                    success: false,
                    message: err.message
                });
            }

            db.run(
                `
                UPDATE ambulances
                SET latitude = ?,
                    longitude = ?,
                    status = ?
                WHERE id = ?
                `,
                [
                    latitude,
                    longitude,
                    status || "En Route",
                    ambulance_id
                ]
            );

            res.status(201).json({
                success: true,
                message: "Location updated"
            });
        }
    );
});


module.exports = router;