import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance in kilometres between two points
    on the earth (lat/lon in decimal degrees)."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _normalize_factor(value, min_val, max_val):
    """Normalize a value to 0-100 range. If value < min_val, return 0. If > max_val, return 100."""
    if max_val <= min_val:
        return 0.0
    if value <= min_val:
        return 0.0
    if value >= max_val:
        return 100.0
    return ((value - min_val) / (max_val - min_val)) * 100.0


def compute_matching_score(listing, request):
    """Compute a matching score out of 100 for a listing against a request.

    Score breakdown:
    - 0.40 × Material Compatibility
    - 0.25 × Quantity Suitability
    - 0.20 × Condition Suitability
    - 0.15 × Distance Suitability
    """

    # Initialize factor scores
    material_score = 0.0
    quantity_score = 0.0
    condition_score = 0.0
    distance_score = 0.0

    # --- Material Compatibility ---
    if listing["material_type"] != request["material_type"]:
        # Incompatible material
        material_score = 0.0
    else:
        # Exact material match
        material_score = 100.0

    # --- Quantity Suitability ---
    try:
        listing_qty = float(listing["quantity"])
        request_qty = float(request["quantity_needed"])
    except (ValueError, TypeError):
        listing_qty = 0
        request_qty = 0

    listing_unit = listing["unit"] or ""
    request_unit = request["unit"] or ""

    # Unit match
    if listing_unit == request_unit:
        if listing_qty >= request_qty:
            quantity_score = 100.0
        else:
            # Insufficient quantity
            ratio = listing_qty / request_qty if request_qty > 0 else 0
            quantity_score = ratio * 100.0
    else:
        # Different units - check for known conversions or reject
        # For MVP: exact unit match required, different units get low score
        quantity_score = 30.0

    # --- Condition Suitability ---
    listing_cond = (listing["condition"] or "").strip().lower()
    min_cond = (request["min_condition"] or "").strip().lower()

    condition_order = ["new", "good", "usable", "needs inspection", "poor"]
    try:
        listing_cond_idx = condition_order.index(listing_cond)
    except ValueError:
        listing_cond_idx = len(condition_order)  # Unknown condition ranked lowest
    try:
        min_cond_idx = condition_order.index(min_cond)
    except ValueError:
        min_cond_idx = len(condition_order)  # Unknown min condition

    if listing_cond_idx <= min_cond_idx:
        # Condition is acceptable or better
        # Score based on how much better
        diff = min_cond_idx - listing_cond_idx
        if diff >= 0:
            condition_score = 100.0 - (diff * 20.0)
            if condition_score < 0:
                condition_score = 0.0
        else:
            condition_score = 100.0
    else:
        # Condition does not meet minimum requirement
        condition_score = 0.0

    # --- Distance Suitability ---
    listing_lat = listing.get("latitude")
    listing_lon = listing.get("longitude")
    request_lat = request.get("latitude")
    request_lon = request.get("longitude")
    max_dist = float(request.get("max_distance_km", 50) or 50)

    if listing_lat is not None and listing_lon is not None and request_lat is not None and request_lon is not None:
        dist = haversine_distance(listing_lat, listing_lon, request_lat, request_lon)
        if dist is None:
            distance_score = 0.0
        elif dist <= 0:
            distance_score = 100.0
        elif dist >= max_dist:
            distance_score = 0.0
        else:
            # Normalized: full score at 0km, 0 at max_dist
            distance_score = 100.0 * (1 - dist / max_dist)
    else:
        # Missing coordinates - do not invent distance
        distance_score = 0.0

    # --- Final Score ---
    final_score = (
        0.40 * material_score
        + 0.25 * quantity_score
        + 0.20 * condition_score
        + 0.15 * distance_score
    )

    return {
        "material_compatibility": material_score,
        "quantity_suitability": quantity_score,
        "condition_suitability": condition_score,
        "distance_suitability": distance_score,
        "score": round(final_score, 1),
    }


def check_eligibility(listing, request):
    """Apply hard eligibility filters. Returns (is_eligible, rejection_reason).

    Reject listings that:
    - Are unavailable.
    - Have an incompatible material category.
    - Have incompatible quantity units.
    - Cannot satisfy the requested quantity.
    - Fail the minimum condition requirement.
    - Exceed the recipient's maximum distance when both parties have valid coordinates.
    - Exceed the recipient's maximum price when a price limit is specified.
    """

    # Check availability
    if listing.get("status", "active") != "active":
        return False, "unavailable"

    # Material category match
    if listing.get("material_type") != request.get("material_type"):
        return False, "incompatible_material"

    # Quantity units compatibility
    listing_unit = (listing.get("unit") or "").strip()
    request_unit = (request.get("unit") or "").strip()
    if listing_unit and request_unit and listing_unit != request_unit:
        # For MVP, different units are ineligible
        return False, "incompatible_units"

    # Check quantity can be satisfied
    try:
        listing_qty = float(listing.get("quantity", 0) or 0)
        request_qty = float(request.get("quantity_needed", 0) or 0)
    except (ValueError, TypeError):
        return False, "invalid_quantity"

    if listing_qty < request_qty:
        return False, "insufficient_quantity"

    # Minimum condition requirement
    listing_cond = (listing.get("condition") or "").strip().lower()
    min_cond = (request.get("min_condition") or "").strip().lower()

    condition_order = ["new", "good", "usable", "needs inspection", "poor"]
    try:
        listing_cond_idx = condition_order.index(listing_cond)
    except ValueError:
        listing_cond_idx = len(condition_order)
    try:
        min_cond_idx = condition_order.index(min_cond)
    except ValueError:
        min_cond_idx = len(condition_order)

    if listing_cond_idx > min_cond_idx:
        return False, "condition_too_low"

    # Distance check
    max_dist = float(request.get("max_distance_km", 50) or 50)
    listing_lat = listing.get("latitude")
    listing_lon = listing.get("longitude")
    request_lat = request.get("latitude")
    request_lon = request.get("longitude")

    if listing_lat is not None and listing_lon is not None and request_lat is not None and request_lon is not None:
        dist = haversine_distance(listing_lat, listing_lon, request_lat, request_lon)
        if dist is not None and dist > max_dist:
            return False, "exceeds_max_distance"

    # Price check
    max_price = float(request.get("max_price", 999999) or 999999)
    listing_price = float(listing.get("price", 0) or 0)
    if listing_price > max_price:
        return False, "exceeds_max_price"

    return True, None