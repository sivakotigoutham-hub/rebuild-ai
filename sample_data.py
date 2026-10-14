import sqlite3
import os
import random
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def init_db():
    """Initialize the database by running database.py's init_db."""
    import database
    database.init_db()


def seed_if_empty():
    """Seed sample data only if the database is empty."""
    import database
    database.init_db()

    conn = database.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]

    if count == 0:
        # Seed users
        now = datetime.now(timezone.utc).isoformat()
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

        cur.execute("SELECT id, name FROM users")
        user_rows = cur.fetchall()
        user_map = {row["name"]: row["id"] for row in user_rows}

        # Seed listings
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

# Seed requests
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

        # Seed enquiries
        enquiries_data = [
            (1, 1, user_map["Alice Martinez"], user_map["Bob Chen"], "Interested in your salvaged red bricks for a community project.", "pending", 0, now, None),
            (2, 2, user_map["Carla Oliveira"], user_map["David Kim"], "Want to take your excess concrete blocks for community garden.", "pending", 0, now, None),
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
    else:
        conn.close()
        print("Database already has data. Skipping seed.")


# For direct execution
if __name__ == "__main__":
    import time
    from datetime import timezone
    seed_if_empty()