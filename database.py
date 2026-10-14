import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_request_by_id(request_id):
    """Fetch a request by id, or return None if it does not exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            organization TEXT,
            email TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            material_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            condition TEXT NOT NULL,
            image_path TEXT,
            location_text TEXT,
            latitude REAL,
            longitude REAL,
            price REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (supplier_id) REFERENCES users (id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_id INTEGER NOT NULL,
            material_type TEXT NOT NULL,
            quantity_needed REAL NOT NULL,
            unit TEXT NOT NULL,
            min_condition TEXT NOT NULL,
            location_text TEXT,
            latitude REAL,
            longitude REAL,
            max_distance_km REAL DEFAULT 50,
            max_price REAL DEFAULT 999999,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (recipient_id) REFERENCES users (id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            request_id INTEGER NOT NULL,
            supplier_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            message TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            quantity_reused REAL DEFAULT 0,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (listing_id) REFERENCES listings (id),
            FOREIGN KEY (request_id) REFERENCES requests (id),
            FOREIGN KEY (supplier_id) REFERENCES users (id),
            FOREIGN KEY (recipient_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()


def seed_sample_data():
    conn = get_connection()
    cur = conn.cursor()

    # Check if data already exists
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    if count > 0:
        conn.close()
        return

    now = datetime.now(timezone.utc).isoformat()

    # Sample users
    users = [
        ("Alice Martinez", "Contractor", "GreenBuild Contractors", "alice@greenbuild.example", now),
        ("Bob Chen", "Construction Manager", "UrbanRenovations Inc.", "bob@urbanren.example", now),
        ("Carla Oliveira", "NGO Coordinator", "EcoCommunity Net", "carla@ecocommunity.example", now),
        ("David Kim", "Individual Homeowner", None, "david@example.com", now),
        ("Elena Rossi", "Project Director", "Sustainable Build Alliance", "elena@sustainablebuild.example", now),
    ]

    for u in users:
        cur.execute(
            "INSERT INTO users (name, role, organization, email, created_at) VALUES (?, ?, ?, ?, ?)",
            u,
        )

    # Refresh users list
    cur.execute("SELECT id, name FROM users")
    user_rows = cur.fetchall()
    user_map = {row["name"]: row["id"] for row in user_rows}

    # Sample listings
    listings_data = [
        (
            user_map["Alice Martinez"],
            "Salvaged Red Bricks",
            "High-quality red bricks from deconstruction project, gently used.",
            "Bricks",
            500,
            "pieces",
            "Good",
            "Portland Depot",
            45.5231,
            -122.6765,
            150,
            "active",
            now,
            now,
        ),
        (
            user_map["Bob Chen"],
            "Excess Concrete Blocks",
            "200 concrete blocks, some still on pallets, others loose.",
            "Concrete Blocks",
            200,
            "pieces",
            "Usable",
            "Site B - South Wing",
            45.5127,
            -122.6613,
            80,
            "active",
            now,
            now,
        ),
        (
            user_map["Carla Oliveira"],
            "Reclaimed Oak Timber",
            "Premium oak beams from historic barn demolition, 3-6m lengths.",
            "Timber",
            15,
            "pieces",
            "Good",
            "Depot North",
            45.4800,
            -122.6100,
            0,
            "active",
            now,
            now,
        ),
        (
            user_map["David Kim"],
            "New Doors",
            "6 interior doors, never installed, pine finish.",
            "Doors",
            6,
            "units",
            "New",
            "Unit 3 - Warehouse",
            45.5300,
            -122.7000,
            120,
            "active",
            now,
            now,
        ),
        (
            user_map["Elena Rossi"],
            "Surplus Tiles",
            "150 ceramic floor tiles, surplus from renovation, assorted patterns.",
            "Tiles",
            150,
            "pieces",
            "Usable",
            "Storage Room A",
            45.5000,
            -122.6500,
            45,
            "active",
            now,
            now,
        ),
    ]

    for l in listings_data:
        cur.execute(
            """
            INSERT INTO listings
            (supplier_id, title, description, material_type, quantity, unit, condition, location_text, latitude, longitude, price, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            l,
        )

    # Sample requests
    requests_data = [
        (
            user_map["Bob Chen"],
            "Bricks",
            300,
            "pieces",
            "Usable",
            "Site B - South Wing",
            45.5127,
            -122.6613,
            50,
            100,
            "open",
            now,
            now,
        ),
        (
            user_map["Carla Oliveira"],
            "Timber",
            10,
            "pieces",
            "Good",
            "Depot North",
            45.4800,
            -122.6100,
            30,
            500,
            "open",
            now,
            now,
        ),
        (
            user_map["David Kim"],
            "Doors",
            4,
            "units",
            "New",
            "Unit 3 - Warehouse",
            45.5300,
            -122.7000,
            20,
            200,
            "open",
            now,
            now,
        ),
        (
            user_map["Alice Martinez"],
            "Tiles",
            100,
            "pieces",
            "Usable",
            "Portland Depot",
            45.5231,
            -122.6765,
            40,
            75,
            "open",
            now,
            now,
        ),
    ]

    for r in requests_data:
        cur.execute(
            """
            INSERT INTO requests
            (recipient_id, material_type, quantity_needed, unit, min_condition, location_text, latitude, longitude, max_distance_km, max_price, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            r,
        )

    # Sample enquiries
    enquiries_data = [
        (
            1,  # listing_id
            1,  # request_id
            user_map["Alice Martinez"],  # supplier_id
            user_map["Bob Chen"],  # recipient_id
            "Interested in your salvaged red bricks for a community project.",
            "pending",
            0,
            now,
            None,
        ),
        (
            2,  # listing_id
            2,  # request_id
            user_map["Carla Oliveira"],  # supplier_id
            user_map["David Kim"],  # recipient_id
            "Want to take your excess concrete blocks for community garden.",
            "pending",
            0,
            now,
            None,
        ),
    ]

    for e in enquiries_data:
        cur.execute(
            """
            INSERT INTO enquiries
            (listing_id, request_id, supplier_id, recipient_id, message, status, quantity_reused, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            e,
        )

    conn.commit()
    conn.close()
    print("Sample data seeded successfully.")