import streamlit as st
import pandas as pd
import os
import sqlite3
import math
from datetime import datetime

# Page config must be first
st.set_page_config(
    page_title="ReBuild AI",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

import database
import image_classifier
import matching

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

st.sidebar.title("ReBuild AI")
st.sidebar.caption("Give materials a second life.")

# Initialize database
if "initialized" not in st.session_state:
    database.init_db()
    st.session_state.initialized = True

# Ensure uploads directory exists
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)


# --- Helper Functions ---

def get_user_id():
    """Get the current demo user ID from sidebar selection."""
    demo_users = ["Alice Martinez", "Bob Chen", "Carla Oliveira", "David Kim", "Elena Rossi"]
    selected = st.sidebar.selectbox(
        "Demo User",
        options=demo_users,
        index=0,
        key="demo_user_selector",
    )
    return selected


def get_user_name():
    return st.session_state.get("demo_user_selector", "Alice Martinez")


def get_current_user():
    name = get_user_name()
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row["id"]
    return None


def safe_filename(original_name):
    """Generate a safe unique filename."""
    import uuid
    ext = original_name.rsplit(".", 1)[-1] if "." in original_name else "png"
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    return safe_name


def get_listings(show_all=False, user_name=None):
    """Get all listings from database, optionally filtered by user."""
    conn = database.get_connection()
    cur = conn.cursor()

    if user_name:
        cur.execute("SELECT id FROM users WHERE name = ?", (user_name,))
        user_row = cur.fetchone()
        if user_row:
            cur.execute(
                "SELECT * FROM listings WHERE supplier_id = ? ORDER BY created_at DESC",
                (user_row["id"],),
            )
        else:
            cur.execute("SELECT * FROM listings ORDER BY created_at DESC")
    else:
        cur.execute("SELECT * FROM listings ORDER BY created_at DESC")

    rows = cur.fetchall()
    conn.close()
    return rows


def get_requests(show_all=False, user_name=None):
    """Get all requests from database."""
    conn = database.get_connection()
    cur = conn.cursor()

    if user_name:
        cur.execute("SELECT id FROM users WHERE name = ?", (user_name,))
        user_row = cur.fetchone()
        if user_row:
            cur.execute(
                "SELECT * FROM requests WHERE recipient_id = ? ORDER BY created_at DESC",
                (user_row["id"],),
            )
        else:
            cur.execute("SELECT * FROM requests ORDER BY created_at DESC")
    else:
        cur.execute("SELECT * FROM requests ORDER BY created_at DESC")

    rows = cur.fetchall()
    conn.close()
    return rows


def get_enquiries(listing_id=None, user_name=None):
    """Get enquiries, optionally filtered by listing or user."""
    conn = database.get_connection()
    cur = conn.cursor()

    if listing_id:
        cur.execute(
            "SELECT * FROM enquiries WHERE listing_id = ? ORDER BY created_at DESC",
            (listing_id,),
        )
    elif user_name:
        cur.execute(
            "SELECT * FROM enquiries WHERE supplier_id = ? OR recipient_id = ? ORDER BY created_at DESC",
            (user_map.get(user_name, 0), user_map.get(user_name, 0)),
        )
    else:
        cur.execute("SELECT * FROM enquiries ORDER BY created_at DESC")

    rows = cur.fetchall()
    conn.close()
    return rows


def get_matches_for_request(request_id):
    """Get eligible listings for a request."""
    from matching import check_eligibility, compute_matching_score

    request = database.get_request_by_id(request_id)
    if not request:
        return []

    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM listings WHERE status = 'active'")
    all_listings = cur.fetchall()
    conn.close()

    matches = []
    for listing in all_listings:
        listing_dict = dict(listing)
        eligible, reason = check_eligibility(listing_dict, request)
        if eligible:
            score_data = compute_matching_score(listing_dict, request)
            matches.append((listing_dict, score_data))

    # Sort by score descending
    matches.sort(key=lambda x: x["score"]["score"], reverse=True)
    return matches


# ... (more helper functions will be added as needed)


# --- Page Functions ---


def home_page():
    """Home dashboard page."""
    st.title("🏗️ ReBuild AI")
    st.caption("Give materials a second life.")

    # Get stats from database
    conn = database.get_connection()
    cur = conn.cursor()

    # Active listings
    cur.execute("SELECT COUNT(*) FROM listings WHERE status = 'active'")
    active_listings = cur.fetchone()[0]

    # Open requests
    cur.execute("SELECT COUNT(*) FROM requests WHERE status = 'open'")
    open_requests = cur.fetchone()[0]

    # Total enquiries
    cur.execute("SELECT COUNT(*) FROM enquiries")
    total_enquiries = cur.fetchone()[0]

    # Confirmed reuse
    cur.execute("SELECT SUM(quantity_reused) FROM enquiries WHERE status = 'completed'")
    reuse_row = cur.fetchone()
    confirmed_reused = reuse_row[0] or 0

    # Quantity by unit
    cur.execute(
        "SELECT unit, SUM(quantity) FROM listings WHERE status = 'active' GROUP BY unit"
    )
    unit_rows = cur.fetchall()
    quantity_by_unit = {row[0]: row[1] for row in unit_rows}

    conn.close()

    # Layout
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Active Listings", active_listings)

    with col2:
        st.metric("Open Requests", open_requests)

    with col3:
        st.metric("Total Enquiries", total_enquiries)

    with col4:
        st.metric("Confirmed Reused", f"{int(confirmed_reused)} pieces")

    st.divider()

    # Recent listings
    st.subheader("Recent Listings")
    listings = get_listings(show_all=False)
    if listings:
        for row in listings[:5]:
            lst = dict(row)
            col_a, col_b = st.columns([1, 3])
            with col_a:
                if lst["image_path"] and os.path.exists(os.path.join(UPLOADS_DIR, lst["image_path"])):
                    st.image(os.path.join(UPLOADS_DIR, lst["image_path"]), width=80)
                else:
                    st.box(height=80, label="No image")
            with col_b:
                st.markdown(f"**{lst['title']}** — {lst['material_type']}")
                st.caption(f"{lst['quantity']} {lst['unit']} | {lst['condition']} | {lst['location_text']}")
    else:
        st.caption("No listings yet. Add one above!")

    # Recommended materials section
    st.subheader("Recommended for You")
    user_name = get_user_name()
    request_rows = get_requests(user_name=user_name)
    if request_rows:
        # Show first open request's matches
        req = dict(request_rows[0])
        st.caption(f"Looking for: {req['material_type']} — {req['quantity_needed']} {req['unit']}")
        matches = get_matches_for_request(req["id"])
        if matches:
            for lst, score_data in matches[:3]:
                with st.container():
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if lst["image_path"] and os.path.exists(os.path.join(UPLOADS_DIR, lst["image_path"])):
                            st.image(os.path.join(UPLOADS_DIR, lst["image_path"]), width=100)
                        else:
                            st.box(height=100, label="No image")
                    with col2:
                        st.markdown(f"**{lst['title']}** — {lst['material_type']}")
                        st.caption(f"{lst['quantity']} {lst['unit']} | {lst['condition']}")
                        st.caption(f"Match: {score_data['score']}/100")
                        # Show factor breakdown
                        cols = st.columns(4)
                        with cols[0]:
                            st.caption(f"Material: {score_data['material_compatibility']}/100")
                        with cols[1]:
                            st.caption(f"Quantity: {score_data['quantity_suitability']}/100")
                        with cols[2]:
                            st.caption(f"Condition: {score_data['condition_suitability']}/100")
                        with cols[3]:
                            st.caption(f"Distance: {score_data['distance_suitability']}/100")
                    st.divider()
        else:
            st.info("No materials match your current request criteria.")
    else:
        st.info("Set up a request in the 'Find Materials' page to get recommendations.")


def list_materials_page():
    """List materials page - form to upload and list materials."""
    st.title("📋 List Materials")
    st.caption("Share surplus construction materials with the community")

    user_name = get_user_name()
    user_id = get_current_user()

    with st.form("material_form", clear_on_submit=True):
        st.subheader("Material Details")

        # Image upload
        st.caption("Material Photograph")
        uploaded_file = st.file_uploader(
            "Upload a photo of the material",
            type=["jpg", "jpeg", "png", "webp"],
            help="Supported formats: JPG, PNG, WebP",
        )

        # Image preview
        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file)
                st.image(image, caption="Preview", width=300)
            except Exception as e:
                st.error(f"Could not load image: {e}")

        # AI-suggested category
        st.caption("AI-Suggested Category")
        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file)
                results = image_classifier.get_top_three_categories(image)
                if results:
                    st.caption("Top suggestions:")
                    for i, (cat, score) in enumerate(results):
                        st.caption(f"{i+1}. {cat}: {score:.1%}")
                else:
                    st.warning("Could not run image classification. Select manually below.")
            except Exception as e:
                st.error(f"Classification failed: {e}")
                st.info("Please select the category manually.")

        # Category selection (with override)
        col_a, col_b = st.columns(2)
        with col_a:
            selected_category = st.selectbox(
                "Material Category",
                options=image_classifier.CATEGORIES,
                index=0,
                label_visibility="collapsed",
            )
        with col_b:
            if uploaded_file is not None:
                if st.button("Override with AI", use_container_width=True):
                    st.session_state["ai_override"] = True

        # If AI failed or user wants manual
        if not uploaded_file or (uploaded_file and st.session_state.get("ai_override", False)):
            selected_category = st.selectbox(
                "Material Category (manual)",
                options=image_classifier.CATEGORIES,
                index=0,
                label_visibility="collapsed",
            )
        elif uploaded_file and not st.session_state.get("ai_override", False):
            # Use AI suggestion but allow override
            selected_category = st.selectbox(
                "Material Category",
                options=image_classifier.CATEGORIES,
                index=0,
                label_visibility="collapsed",
            )
            st.caption(image_classifier.get_disclaimer())

        # Form fields
        title = st.text_input("Listing Title", placeholder="e.g., Salvaged Red Bricks")
        description = st.text_area("Description", placeholder="Describe the material condition, size, etc.")

        col1, col2 = st.columns(2)
        with col1:
            quantity = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
        with col2:
            unit = st.selectbox(
                "Unit",
                options=["pieces", "units", "m²", "m³", "kg", "tonnes"],
                index=0,
                label_visibility="collapsed",
            )

        col3, col4 = st.columns(2)
        with col3:
            condition = st.selectbox(
                "Condition",
                options=["Good", "Usable", "Needs Inspection"],
                index=0,
                label_visibility="collapsed",
            )
        with col4:
            location = st.text_input("Location Name", placeholder="Portland Depot")

        lat_col, lon_col = st.columns(2)
        with lat_col:
            latitude = st.number_input("Latitude", value=0.0, step=0.0001, format="%.4f")
        with lon_col:
            longitude = st.number_input("Longitude", value=0.0, step=0.0001, format="%.4f")

        price = st.number_input("Asking Price (0 = free)", min_value=0, value=0, step=5)

        submitted = st.form_submit_button("Save Listing")

        if submitted:
            # Validation
            errors = []

            if not title.strip():
                errors.append("Title is required.")
            if not selected_category:
                errors.append("Material category is required.")
            if not description.strip():
                errors.append("Description is required.")
            if quantity <= 0:
                errors.append("Quantity must be greater than 0.")
            if latitude == 0 and longitude == 0:
                latitude = None
                longitude = None

            # Image handling
            image_path = None
            if uploaded_file is not None:
                filename = safe_filename(uploaded_file.name)
                save_path = os.path.join(UPLOADS_DIR, filename)
                try:
                    img = Image.open(uploaded_file)
                    img.save(save_path)
                    image_path = filename
                except Exception as e:
                    errors.append(f"Could not save image: {e}")

            if errors:
                for e_msg in errors:
                    st.error(e_msg)
            else:
                # Save to database
                conn = database.get_connection()
                cur = conn.cursor()

                # Use AI-suggested category or manual
                confirmed_category = selected_category

                cur.execute(
                    """
                    INSERT INTO listings
                    (supplier_id, title, description, material_type, quantity, unit, condition, image_path, location_text, latitude, longitude, price, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        title.strip(),
                        description.strip(),
                        confirmed_category,
                        quantity,
                        unit,
                        condition,
                        image_path,
                        location.strip() if location else None,
                        latitude if latitude else None,
                        longitude if longitude else None,
                        price,
                        "active",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ),
                )

                conn.commit()
                conn.close()

                # Re-run classification and save result
                if uploaded_file is not None:
                    try:
                        image = Image.open(uploaded_file)
                        classifier_results = image_classifier.get_top_three_categories(image)
                        if classifier_results:
                            # Save the confirmed category (already done above)
                            pass
                    except Exception:
                        pass

                st.success("Listing saved successfully!")
                st.rerun()

    # Reset override state
    if "ai_override" in st.session_state:
        del st.session_state["ai_override"]


def find_materials_page():
    """Find materials page - recipients can specify needs and find matches."""
    st.title("🔍 Find Materials")
    st.caption("Search for surplus materials that match your needs")

    with st.form("request_form"):
        st.subheader("Your Requirements")

        col1, col2 = st.columns(2)
        with col1:
            material_type = st.selectbox(
                "Material Category Needed",
                options=[
                    "Bricks",
                    "Concrete Blocks",
                    "Timber",
                    "Tiles",
                    "Steel",
                    "Other Metal",
                    "Sand",
                    "Gravel",
                    "Doors",
                    "Windows",
                    "Plumbing Fixtures",
                    "Electrical Fixtures",
                    "Other",
                ],
                index=0,
                label_visibility="collapsed",
            )
        with col2:
            quantity_needed = st.number_input(
                "Quantity Required", min_value=0.0, value=1.0, step=1.0, label_visibility="collapsed"
            )

        col3, col4 = st.columns(2)
        with col3:
            unit = st.selectbox(
                "Unit",
                options=["pieces", "units", "m²", "m³", "kg", "tonnes"],
                index=0,
                label_visibility="collapsed",
            )
        with col4:
            min_condition = st.selectbox(
                "Minimum Acceptable Condition",
                options=["Good", "Usable", "Needs Inspection"],
                index=0,
                label_visibility="collapsed",
            )

        location_text = st.text_input("Location", placeholder="e.g., Site B - South Wing")
        lat_col, lon_col = st.columns(2)
        with lat_col:
            request_lat = st.number_input("Latitude", value=0.0, step=0.0001, format="%.4f")
        with lon_col:
            request_lon = st.number_input("Longitude", value=0.0, step=0.0001, format="%.4f")

        max_distance = st.number_input(
            "Maximum Travel Distance (km)",
            min_value=0,
            value=50,
            step=5,
            label_visibility="collapsed",
        )
        max_price = st.number_input(
            "Maximum Price",
            min_value=0,
            value=999999,
            step=10,
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button("Find Matches")

        if submitted:
            # Build request dict for matching
            from matching import check_eligibility, compute_matching_score

            request = {
                "material_type": material_type,
                "quantity_needed": quantity_needed,
                "unit": unit,
                "min_condition": min_condition,
                "location_text": location_text or None,
                "latitude": request_lat if request_lat else None,
                "longitude": request_lon if request_lon else None,
                "max_distance_km": max_distance,
                "max_price": max_price,
            }

            # Get all active listings
            conn = database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM listings WHERE status = 'active'")
            all_listings = cur.fetchall()
            conn.close()

            # Check eligibility and compute scores
            results = []
            for row in all_listings:
                listing = dict(row)
                eligible, reason = check_eligibility(listing, request)
                if eligible:
                    score_data = compute_matching_score(listing, request)
                    # Calculate distance
                    listing_lat = listing.get("latitude")
                    listing_lon = listing.get("longitude")
                    if listing_lat is not None and listing_lon is not None and request_lat and request_lon:
                        dist = matching.haversine_distance(listing_lat, listing_lon, request_lat, request_lon)
                    else:
                        dist = None
                    results.append((listing, score_data, dist))

            if results:
                # Sort by score descending
                results.sort(key=lambda x: x[1]["score"], reverse=True)

                st.subheader(f"Found {len(results)} matching material(s)")

                for listing, score_data, dist in results:
                    # Get image
                    image_path = listing["image_path"]
                    img_url = None
                    if image_path and os.path.exists(os.path.join(UPLOADS_DIR, image_path)):
                        img_url = os.path.join(UPLOADS_DIR, image_path)

                    with st.container():
                        st.divider()
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            if img_url:
                                st.image(img_url, width=150)
                            else:
                                st.box(height=150, label="No image")
                        with col2:
                            st.markdown(f"**{listing['title']}**")
                            st.caption(f"{listing['material_type']} | {listing['quantity']} {listing['unit']}")
                            st.caption(f"Condition: {listing['condition']}")

                            # Location and distance
                            location_parts = [listing["location_text"] or ""]
                            if listing_lat is not None and listing_lon is not None and request_lat and request_lon:
                                if dist is not None:
                                    location_parts.append(f"~{dist:.0f} km away")
                            st.caption(" | ".join(filter(None, location_parts)))

                            # Price
                            st.caption(f"Asking Price: ${listing['price'] or 0}")

# Match score and breakdown
                            st.markdown(f"**Match Score: {score_data['score']}/100**")
                            st.caption(
                                f"Material: {score_data['material_compatibility']}/100 · "
                                f"Quantity: {score_data['quantity_suitability']}/100 · "
                                f"Condition: {score_data['condition_suitability']}/100 · "
                                f"Distance: {score_data['distance_suitability']}/100"
                            )

                                # Enquiry button
                                recipient_name = get_user_name()
                                if st.button(
                                    f"Send Enquiry →",
                                    key=f"enquire_{listing['id']}_{request['id']}",
                                    use_container_width=True,
                                ):
                                    # Create enquiry
                                    supplier_id = listing["supplier_id"]
                                    recipient_id = get_current_user()
                                    if recipient_id is None:
                                        st.error("Please select a demo user first.")
                                    else:
                                        message = f"Interest in your {listing['title']} for {request['material_type']}."
                                        conn2 = database.get_connection()
                                        cur2 = conn2.cursor()
                                        try:
                                            cur2.execute(
                                                """
                                                INSERT INTO enquiries
                                                (listing_id, request_id, supplier_id, recipient_id, message, status, quantity_reused, updated_at, completed_at)
                                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                            """,
                                                (
                                                    listing["id"],
                                                    request["id"] if "id" in request else 0,
                                                    supplier_id,
                                                    recipient_id,
                                                    message,
                                                    "pending",
                                                    0,
                                                    datetime.now().isoformat(),
                                                    None,
                                                ),
                                            )
                                            conn2.commit()
                                            conn2.close()
                                            st.success("Enquiry sent successfully!")
                                        except Exception as e:
                                            conn2.close()
                                            st.error(f"Failed to send enquiry: {e}")
            else:
                st.info("No suitable materials available with the current criteria.")


def my_listings_page():
    """My listings and enquiries management page."""
    st.title("👤 My Listings & Enquiries")
    st.caption("Manage your materials and track enquiries")

    user_name = get_user_name()
    user_id = get_current_user()

    # Get user's listings
    listings = get_listings(user_name=user_name)

    # Get user's enquiries (both sent and received)
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE name = ?", (user_name,))
    user_row = cur.fetchone()
    user_db_id = user_row["id"] if user_row else 0

    # Enquiries sent (supplier)
    cur.execute(
        "SELECT * FROM enquiries WHERE supplier_id = ? ORDER BY created_at DESC",
        (user_db_id,),
    )
    sent_enquiries = cur.fetchall()

    # Enquiries received (recipient)
    cur.execute(
        "SELECT * FROM enquiries WHERE recipient_id = ? ORDER BY created_at DESC",
        (user_db_id,),
    )
    received_enquiries = cur.fetchall()

    conn.close()

    tab1, tab2 = st.tabs(["My Listings", "Enquiries"])

    with tab1:
        st.subheader("Your Listings")
        if listings:
            for row in listings:
                lst = dict(row)
                with st.container():
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        if lst["image_path"] and os.path.exists(os.path.join(UPLOADS_DIR, lst["image_path"])):
                            st.image(os.path.join(UPLOADS_DIR, lst["image_path"]), width=100)
                        else:
                            st.box(height=100, label="No image")
                    with col2:
                        st.markdown(f"**{lst['title']}**")
                        st.caption(f"{lst['material_type']} | {lst['quantity']} {lst['unit']} | {lst['condition']}")
                        st.caption(f"Location: {lst['location_text'] or 'N/A'}")
                        st.caption(f"Price: ${lst['price'] or 0}")
                    with col3:
                        # Availability toggle
                        new_status = st.selectbox(
                            "Status",
                            options=["active", "inactive"],
                            index=0 if lst["status"] == "active" else 1,
                            key=f"status_{lst['id']}",
                        )
                        if st.button("Update", key=f"update_{lst['id']}"):
                            conn2 = database.get_connection()
                            cur2 = conn2.cursor()
                            cur2.execute(
                                "UPDATE listings SET status = ?, updated_at = ? WHERE id = ?",
                                (new_status, datetime.now().isoformat(), lst["id"]),
                            )
                            conn2.commit()
                            conn2.close()
                            st.success("Status updated!")
                            st.rerun()
        else:
            st.info("No listings found. Add materials using the 'List Materials' page.")

    with tab2:
        st.subheader("Your Enquiries")

        st.write("**Sent Enquiries** (you're the supplier)")
        if sent_enquiries:
            for env in sent_enquiries:
                env_dict = dict(env)
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if env_dict.get("image_path") and env_dict.get("image_path") and os.path.exists(
                            os.path.join(UPLOADS_DIR, env_dict["image_path"])
                        ):
                            st.image(os.path.join(UPLOADS_DIR, env_dict["image_path"]), width=80)
                        else:
                            st.box(height=80, label="No image")
                    with col2:
                        st.markdown(f"**{env_dict.get('listing_title', '')}**")
                        st.caption(f"Listing ID: {env_dict.get('listing_id', '')} | Request ID: {env_dict.get('request_id', '')}")
                        st.caption(f"Status: {env_dict.get('status', 'pending')}")
                    with col3:
                        # Accept/Reject action
                        action = st.selectbox(
                            "Action",
                            options=["pending", "accepted", "rejected"],
                            index=0,
                            key=f"env_action_{env_dict['id']}",
                            on_change=lambda: st.rerun(),
                        )
                        if st.button("Apply", key=f"apply_{env_dict['id']}"):
                            conn2 = database.get_connection()
                            cur2 = conn2.cursor()
                            cur2.execute(
                                "UPDATE enquiries SET status = ?, updated_at = ? WHERE id = ?",
                                (action, datetime.now().isoformat(), env_dict["id"]),
                            )
                            conn2.commit()
                            conn2.close()
                            st.success(f"Enquiry {action}!")
                            st.rerun()
        else:
            st.info("No sent enquiries.")

        st.write("**Received Enquiries** (you're the recipient)")
        if received_enquiries:
            for env in received_enquiries:
                env_dict = dict(env)
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if env_dict.get("image_path") and os.path.exists(
                            os.path.join(UPLOADS_DIR, env_dict["image_path"])
                        ):
                            st.image(os.path.join(UPLOADS_DIR, env_dict["image_path"]), width=80)
                        else:
                            st.box(height=80, label="No image")
                    with col2:
                        st.markdown(f"**{env_dict.get('listing_title', '')}**")
                        st.caption(f"Material: {env_dict.get('material_type', '')}")
                        st.caption(f"Status: {env_dict.get('status', 'pending')}")
                    with col3:
                        # Accept/Reject and mark completed
                        action = st.selectbox(
                            "Action",
                            options=["pending", "accepted", "rejected"],
                            index=0,
                            key=f"recv_env_{env_dict['id']}",
                        )
                        quantity_reused = st.number_input(
                            "Quantity Reused",
                            min_value=0,
                            value=env_dict.get("quantity_reused", 0) or 0,
                            key=f"qty_{env_dict['id']}",
                        )
                        if st.button("Apply", key=f"apply_recv_{env_dict['id']}"):
                            conn2 = database.get_connection()
                            cur2 = conn2.cursor()
                            cur2.execute(
                                "UPDATE enquiries SET status = ?, quantity_reused = ?, updated_at = ?, completed_at = ? WHERE id = ?",
                                (action, quantity_reused, datetime.now().isoformat(), datetime.now().isoformat(), env_dict["id"]),
                            )
                            conn2.commit()
                            conn2.close()
                            st.success(f"Enquiry {action} with {quantity_reused} reused!")
                            st.rerun()
        else:
            st.info("No received enquiries.")


def impact_dashboard_page():
    """Impact dashboard page with statistics and charts."""
    st.title("📊 Impact Dashboard")
    st.caption("ReBuild AI impact metrics")

    conn = database.get_connection()
    cur = conn.cursor()

    # Active listings
    cur.execute("SELECT COUNT(*) FROM listings WHERE status = 'active'")
    active_listings = cur.fetchone()[0]

    # Total quantity listed by unit
    cur.execute("SELECT unit, SUM(quantity) FROM listings WHERE status = 'active' GROUP BY unit")
    unit_rows = cur.fetchall()
    total_by_unit = {row[0]: row[1] or 0 for row in unit_rows}

    # Total enquiries
    cur.execute("SELECT COUNT(*) FROM enquiries")
    total_enquiries = cur.fetchone()[0]

    # Confirmed reuse events
    cur.execute("SELECT COUNT(*) FROM enquiries WHERE status = 'completed'")
    confirmed_events = cur.fetchone()[0]

    # Confused reused quantities by unit
    cur.execute(
        "SELECT l.unit, SUM(e.quantity_reused) FROM enquiries e "
        "JOIN listings l ON e.listing_id = l.id "
        "WHERE e.status = 'completed' AND l.status = 'active' "
        "GROUP BY l.unit"
    )
    reuse_unit_rows = cur.fetchall()
    confirmed_by_unit = {row[0]: row[1] or 0 for row in reuse_unit_rows}

    # Listings by material category
    cur.execute(
        "SELECT material_type, COUNT(*) FROM listings WHERE status = 'active' GROUP BY material_type"
    )
    cat_rows = cur.fetchall()
    listings_by_category = {row[0]: row[1] for row in cat_rows}

    # Listing statuses
    cur.execute("SELECT status, COUNT(*) FROM listings GROUP BY status")
    status_rows = cur.fetchall()
    status_distribution = {row[0]: row[1] for row in status_rows}

    # Recent completed enquiries
    cur.execute(
        "SELECT e.*, l.title, l.material_type "
        "FROM enquiries e "
        "JOIN listings l ON e.listing_id = l.id "
        "WHERE e.status = 'completed' "
        "ORDER BY e.completed_at DESC LIMIT 5"
    )
    recent_completed = cur.fetchall()

    conn.close()

    # Layout
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Active Listings", active_listings)

    with col2:
        st.metric("Total Enquiries", total_enquiries)

    with col3:
        st.metric("Confirmed Reuse Events", confirmed_events)

    with col4:
        st.metric("Total Quantity Reused", f"{int(sum(confirmed_by_unit.values()))} pieces")

    st.divider()

    # Charts
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Listings by Material Category")
        if listings_by_category:
            cat_df = pd.DataFrame(
                list(listings_by_category.items()), columns=["Category", "Count"]
            )
            st.bar_chart(cat_df.set_index("Category"))
        else:
            st.caption("No data available.")

    with col_right:
        st.subheader("Listing Statuses")
        if status_distribution:
            status_df = pd.DataFrame(
                list(status_distribution.items()), columns=["Status", "Count"]
            )
            st.pie_chart(status_df, values="Count", names="Status")
        else:
            st.caption("No data available.")

    # Secondary row of charts
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("Quantity Listed by Unit")
        if total_by_unit:
            unit_df = pd.DataFrame(
                list(total_by_unit.items()), columns=["Unit", "Quantity"]
            )
            st.bar_chart(unit_df.set_index("Unit"))
        else:
            st.caption("No data available.")

    with col_right2:
        st.subheader("Confirmed Reused by Unit")
        if confirmed_by_unit:
            reuse_df = pd.DataFrame(
                list(confirmed_by_unit.items()), columns=["Unit", "Quantity"]
            )
            st.bar_chart(reuse_df.set_index("Unit"))
        else:
            st.caption("No data available.")

    # Recent completed enquiries
    st.subheader("Recent Confirmed Reuse Events")
    if recent_completed:
        for env in recent_completed:
            env_dict = dict(env)
            lst = env_dict.get("listing_title", "")
            mat = env_dict.get("material_type", "")
            qty = env_dict.get("quantity_reused", 0)
            comp = env_dict.get("completed_at", "")
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    img_path = env_dict.get("image_path")
                    if img_path and os.path.exists(os.path.join(UPLOADS_DIR, img_path)):
                        st.image(os.path.join(UPLOADS_DIR, img_path), width=60)
                    else:
                        st.box(height=60, label="No image")
                with col2:
                    st.markdown(f"**{lst}** — {mat}")
                    st.caption(f"Quantity reused: {qty}")
                    if comp:
                        st.caption(f"Completed: {comp[:10]}")
    else:
        st.info("No confirmed reuse events yet.")


# --- Main App ---

def main():
    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        options=[
            "Home",
            "List Materials",
            "Find Materials",
            "My Listings & Enquiries",
            "Impact Dashboard",
        ],
        index=0,
    )

    # Display appropriate page
    if page == "Home":
        home_page()
    elif page == "List Materials":
        list_materials_page()
    elif page == "Find Materials":
        find_materials_page()
    elif page == "My Listings & Enquiries":
        my_listings_page()
    elif page == "Impact Dashboard":
        impact_dashboard_page()


if __name__ == "__main__":
    main()