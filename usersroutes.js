const express = require("express");
const router = express.Router();
const db = require("../database");

// GET USERS
router.get("/", (req, res) => {

    db.all(
        `
        SELECT
            id,
            name,
            email,
            role,
            status,
            created_at
        FROM users
        ORDER BY id DESC
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


// ADD USER
router.post("/", (req, res) => {

    const {
        name,
        email,
        password,
        role
    } = req.body;

    if (!name || !email || !password || !role) {
        return res.status(400).json({
            success: false,
            message: "All user fields are required"
        });
    }

    db.run(
        `
        INSERT INTO users
        (name, email, password, role)
        VALUES (?, ?, ?, ?)
        `,
        [name, email, password, role],
        function(err) {

            if (err) {
                return res.status(500).json({
                    success: false,
                    message: err.message
                });
            }

            res.status(201).json({
                success: true,
                message: "User created successfully",
                id: this.lastID
            });
        }
    );
});


// UPDATE USER STATUS
router.put("/:id/status", (req, res) => {

    const { status } = req.body;

    db.run(
        `UPDATE users SET status = ? WHERE id = ?`,
        [status, req.params.id],
        function(err) {

            if (err) {
                return res.status(500).json({
                    success: false,
                    message: err.message
                });
            }

            res.json({
                success: true,
                message: "User status updated"
            });
        }
    );
});


module.exports = router;