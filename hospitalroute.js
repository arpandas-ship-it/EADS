const express = require("express");
const router = express.Router();
const db = require("../database");

// GET HOSPITALS
router.get("/", (req, res) => {

    db.all(
        `SELECT * FROM hospitals ORDER BY id DESC`,
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


// GET AVAILABLE HOSPITALS
router.get("/available", (req, res) => {

    db.all(
        `
        SELECT *
        FROM hospitals
        WHERE emergency_available = 'Yes'
        AND available_beds > 0
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


// ADD HOSPITAL
router.post("/", (req, res) => {

    const {
        name,
        location,
        phone,
        emergency_available,
        available_beds
    } = req.body;

    if (!name || !location) {
        return res.status(400).json({
            success: false,
            message: "Hospital name and location are required"
        });
    }

    db.run(
        `
        INSERT INTO hospitals
        (
            name,
            location,
            phone,
            emergency_available,
            available_beds
        )
        VALUES (?, ?, ?, ?, ?)
        `,
        [
            name,
            location,
            phone || "",
            emergency_available || "Yes",
            available_beds || 0
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
                message: "Hospital added successfully",
                id: this.lastID
            });
        }
    );
});


module.exports = router;