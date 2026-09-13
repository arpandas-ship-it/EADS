const sqlite3 = require("sqlite3").verbose();

const db = new sqlite3.Database("./eads.db", (err) => {
    if (err) {
        console.error("Database connection failed:", err.message);
    } else {
        console.log("Connected to EADS database.");
    }
});

db.serialize(() => {

    // USERS
    db.run(`
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // AMBULANCES
    db.run(`
        CREATE TABLE IF NOT EXISTS ambulances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ambulance_number TEXT UNIQUE NOT NULL,
            driver_name TEXT,
            crew_name TEXT,
            type TEXT,
            status TEXT DEFAULT 'Available',
            location TEXT,
            latitude REAL,
            longitude REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // HOSPITALS
    db.run(`
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT,
            emergency_available TEXT DEFAULT 'Yes',
            available_beds INTEGER DEFAULT 0,
            latitude REAL,
            longitude REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // EMERGENCIES
    db.run(`
        CREATE TABLE IF NOT EXISTS emergencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id TEXT UNIQUE NOT NULL,
            caller_name TEXT NOT NULL,
            emergency_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT,
            patient_name TEXT,
            patient_age INTEGER,
            condition TEXT,
            ambulance_id INTEGER,
            hospital_id INTEGER,
            status TEXT DEFAULT 'Pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ambulance_id) REFERENCES ambulances(id),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        )
    `);

    // TRACKING
    db.run(`
        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ambulance_id INTEGER NOT NULL,
            emergency_id INTEGER,
            latitude REAL,
            longitude REAL,
            status TEXT,
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ambulance_id) REFERENCES ambulances(id),
            FOREIGN KEY (emergency_id) REFERENCES emergencies(id)
        )
    `);

    // DISPATCH RECORDS
    db.run(`
        CREATE TABLE IF NOT EXISTS dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER NOT NULL,
            ambulance_id INTEGER NOT NULL,
            dispatcher_id INTEGER,
            dispatched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Dispatched',
            FOREIGN KEY (emergency_id) REFERENCES emergencies(id),
            FOREIGN KEY (ambulance_id) REFERENCES ambulances(id),
            FOREIGN KEY (dispatcher_id) REFERENCES users(id)
        )
    `);

    // DEFAULT USERS
    db.run(`
        INSERT OR IGNORE INTO users
        (name, email, password, role)
        VALUES
        ('Administrator', 'admin@eads.com', 'admin123', 'Administrator')
    `);

    // DEFAULT AMBULANCES
    db.run(`
        INSERT OR IGNORE INTO ambulances
        (ambulance_number, driver_name, crew_name, type, status, location)
        VALUES
        ('AMB-001', 'Raj Kumar', 'Medical Team A', 'Advanced Life Support', 'Available', 'City Center'),
        ('AMB-002', 'Amit Sharma', 'Medical Team B', 'Basic Life Support', 'Available', 'North Zone'),
        ('AMB-003', 'Rahul Das', 'Medical Team C', 'Advanced Life Support', 'En Route', 'South Zone')
    `);

    // DEFAULT HOSPITALS
    db.run(`
        INSERT INTO hospitals
        (name, location, phone, emergency_available, available_beds)
        SELECT 'City General Hospital',
               'Central Avenue',
               '9876543210',
               'Yes',
               25
        WHERE NOT EXISTS (
            SELECT 1 FROM hospitals
            WHERE name = 'City General Hospital'
        )
    `);

});

module.exports = db;