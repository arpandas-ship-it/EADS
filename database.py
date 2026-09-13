import sqlite3
from pathlib import Path

# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "eads.db"


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    # Foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def init_database():

    conn = get_connection()
    cursor = conn.cursor()

    # ==================================================
    # EMERGENCIES
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            emergency_code TEXT UNIQUE NOT NULL,

            caller_name TEXT NOT NULL,
            caller_phone TEXT NOT NULL,

            emergency_type TEXT NOT NULL,

            priority TEXT NOT NULL
                CHECK(priority IN (
                    'CRITICAL',
                    'HIGH',
                    'MEDIUM',
                    'LOW'
                )),

            description TEXT,

            location TEXT NOT NULL,

            latitude REAL,
            longitude REAL,

            status TEXT NOT NULL DEFAULT 'RECEIVED'
                CHECK(status IN (
                    'RECEIVED',
                    'VERIFIED',
                    'DISPATCHED',
                    'EN_ROUTE',
                    'ON_SCENE',
                    'TRANSPORTING',
                    'COMPLETED',
                    'CANCELLED'
                )),

            ambulance_id INTEGER,

            hospital_id INTEGER,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            verified_at DATETIME,

            dispatched_at DATETIME,

            completed_at DATETIME,

            FOREIGN KEY (ambulance_id)
                REFERENCES ambulances(id)
                ON DELETE SET NULL,

            FOREIGN KEY (hospital_id)
                REFERENCES hospitals(id)
                ON DELETE SET NULL
        )
    """)


    # ==================================================
    # AMBULANCES
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ambulances (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            ambulance_number TEXT UNIQUE NOT NULL,

            driver_name TEXT,

            contact_number TEXT,

            ambulance_type TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'AVAILABLE'
                CHECK(status IN (
                    'AVAILABLE',
                    'ASSIGNED',
                    'EN_ROUTE',
                    'ON_SCENE',
                    'TRANSPORTING',
                    'MAINTENANCE',
                    'OFFLINE'
                )),

            latitude REAL,

            longitude REAL,

            current_location TEXT,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ==================================================
    # HOSPITALS
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            hospital_name TEXT NOT NULL,

            address TEXT NOT NULL,

            phone TEXT,

            emergency_available INTEGER DEFAULT 1,

            available_beds INTEGER DEFAULT 0,

            icu_available INTEGER DEFAULT 0,

            latitude REAL,

            longitude REAL,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ==================================================
    # USERS
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT NOT NULL
                CHECK(role IN (
                    'ADMIN',
                    'DISPATCHER',
                    'DRIVER',
                    'HOSPITAL'
                )),

            phone TEXT,

            status TEXT DEFAULT 'ACTIVE',

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ==================================================
    # EMERGENCY STATUS HISTORY
    # ==================================================
    #
    # This is especially important for the emergency
    # module. Every status change is recorded.
    #
    # Example:
    #
    # RECEIVED
    #     ↓
    # VERIFIED
    #     ↓
    # DISPATCHED
    #     ↓
    # EN_ROUTE
    #     ↓
    # ON_SCENE
    #     ↓
    # TRANSPORTING
    #     ↓
    # COMPLETED
    #
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            emergency_id INTEGER NOT NULL,

            old_status TEXT,

            new_status TEXT NOT NULL,

            changed_by TEXT,

            notes TEXT,

            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (emergency_id)
                REFERENCES emergencies(id)
                ON DELETE CASCADE
        )
    """)


    # ==================================================
    # DISPATCH RECORDS
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispatch_records (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            emergency_id INTEGER NOT NULL,

            ambulance_id INTEGER NOT NULL,

            dispatcher_name TEXT,

            dispatch_time DATETIME DEFAULT CURRENT_TIMESTAMP,

            arrival_time DATETIME,

            completion_time DATETIME,

            FOREIGN KEY (emergency_id)
                REFERENCES emergencies(id)
                ON DELETE CASCADE,

            FOREIGN KEY (ambulance_id)
                REFERENCES ambulances(id)
                ON DELETE CASCADE
        )
    """)


    # ==================================================
    # SAMPLE AMBULANCES
    # ==================================================

    cursor.execute("""
        INSERT OR IGNORE INTO ambulances
        (
            ambulance_number,
            driver_name,
            contact_number,
            ambulance_type,
            status,
            current_location
        )
        VALUES
        ('AMB-001', 'Rahul Sharma', '9000000001',
         'Advanced Life Support', 'AVAILABLE', 'City Center'),

        ('AMB-002', 'Amit Das', '9000000002',
         'Basic Life Support', 'AVAILABLE', 'North Zone'),

        ('AMB-003', 'Rohit Singh', '9000000003',
         'Advanced Life Support', 'EN_ROUTE', 'East Zone'),

        ('AMB-004', 'Vikash Roy', '9000000004',
         'Basic Life Support', 'AVAILABLE', 'West Zone')
    """)


    # ==================================================
    # SAMPLE HOSPITALS
    # ==================================================

    cursor.execute("""
        INSERT OR IGNORE INTO hospitals
        (
            hospital_name,
            address,
            phone,
            emergency_available,
            available_beds,
            icu_available
        )
        VALUES
        (
            'City General Hospital',
            'Main Road',
            '03300000001',
            1,
            25,
            6
        ),

        (
            'Life Care Hospital',
            'North Avenue',
            '03300000002',
            1,
            18,
            4
        ),

        (
            'Emergency Medical Center',
            'East Road',
            '03300000003',
            1,
            12,
            3
        )
    """)


    conn.commit()
    conn.close()

    print("Database initialized successfully.")
    print(f"Database location: {DATABASE}")


# --------------------------------------------------
# RUN DIRECTLY
# --------------------------------------------------

if __name__ == "__main__":
    init_database()