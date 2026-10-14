import pytest
import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__) or ".")

from matching import haversine_distance, check_eligibility, compute_matching_score


class TestHaversineDistance:
    """Test Haversine distance calculations."""

    def test_basic_distance(self):
        """Test distance between two known points."""
        # New York City to Philadelphia approx 129 km
        dist = haversine_distance(40.7128, -74.0060, 39.9526, -75.1652)
        assert 120 < dist < 140

    def test_same_point(self):
        """Distance from a point to itself should be 0."""
        dist = haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert dist == 0.0

    def test_missing_coordinates(self):
        """None coordinates should return None."""
        dist = haversine_distance(None, None, None, None)
        assert dist is None

    def test_one_missing(self):
        """Partial missing coordinates should return None."""
        dist = haversine_distance(40.7128, -74.0060, None, None)
        assert dist is None


class TestCheckEligibility:
    """Test hard eligibility filters."""

    def setup_method(self):
        """Set up test data before each test."""
        self.listing_active = {
            "material_type": "Bricks",
            "quantity": 500,
            "unit": "pieces",
            "condition": "Good",
            "location_text": "Portland Depot",
            "latitude": 45.5231,
            "longitude": -122.6765,
            "price": 50,  # Reduced to pass max_price check
            "status": "active",
        }

        self.listing_inactive = {
            "material_type": "Bricks",
            "quantity": 500,
            "unit": "pieces",
            "condition": "Good",
            "location_text": "Portland Depot",
            "latitude": 45.5231,
            "longitude": -122.6765,
            "price": 150,
            "status": "inactive",
        }

        self.request_open = {
            "material_type": "Bricks",
            "quantity_needed": 300,
            "unit": "pieces",
            "min_condition": "Good",
            "location_text": "Site B - South Wing",
            "latitude": 45.5127,
            "longitude": -122.6613,
            "max_distance_km": 50,
            "max_price": 100,
            "status": "open",
        }

    def test_inactive_listing(self):
        """Inactive listings should be rejected."""
        eligible, reason = check_eligibility(self.listing_inactive, self.request_open)
        assert eligible is False
        assert reason == "unavailable"

    def test_material_mismatch(self):
        """Incompatible material category should be rejected."""
        listing = dict(self.listing_active)
        listing["material_type"] = "Timber"
        eligible, reason = check_eligibility(listing, self.request_open)
        assert eligible is False
        assert reason == "incompatible_material"

    def test_insufficient_quantity(self):
        """Listings with insufficient quantity should be rejected."""
        listing = dict(self.listing_active)
        listing["quantity"] = 100  # Only 100, need 300
        eligible, reason = check_eligibility(listing, self.request_open)
        assert eligible is False
        assert reason == "insufficient_quantity"

    def test_condition_too_low(self):
        """Listing condition below minimum requirement."""
        listing = dict(self.listing_active)
        listing["condition"] = "Poor"
        eligible, reason = check_eligibility(listing, self.request_open)
        assert eligible is False
        assert reason == "condition_too_low"

    def test_within_distance(self):
        """Listing within max distance should pass."""
        # Same coords essentially
        listing = dict(self.listing_active)
        listing["latitude"] = 45.5127
        listing["longitude"] = -122.6613
        eligible, reason = check_eligibility(listing, self.request_open)
        assert eligible is True
        assert reason is None

    def test_exceeds_distance(self):
        """Listing exceeding max distance should be rejected."""
        listing = dict(self.listing_active)
        listing["latitude"] = 90.0  # Very far
        listing["longitude"] = -180.0
        eligible, reason = check_eligibility(listing, self.request_open)
        assert eligible is False
        assert reason == "exceeds_max_distance"

    def test_exceeds_max_price(self):
        """Listing exceeding max price should be rejected."""
        listing = dict(self.listing_active)
        listing["price"] = 500  # Way above max of 100
        eligible, reason = check_eligibility(listing, self.request_open)
        assert eligible is False
        assert reason == "exceeds_max_price"

    def test_different_units(self):
        """Different units should be rejected."""
        listing = dict(self.listing_active)
        listing["unit"] = "m³"
        eligible, reason = check_eligibility(listing, self.request_open)
        assert eligible is False
        assert reason == "incompatible_units"


class TestComputeMatchingScore:
    """Test matching score calculation."""

    def test_exact_material_match(self):
        """Exact material match should give 100/100 for material."""
        listing = {
            "material_type": "Bricks",
            "quantity": 500,
            "unit": "pieces",
            "condition": "Good",
            "latitude": 45.5,
            "longitude": -122.7,
            "price": 150,
            "status": "active",
        }
        request = {
            "material_type": "Bricks",
            "quantity_needed": 300,
            "unit": "pieces",
            "min_condition": "Good",
            "latitude": 45.5,
            "longitude": -122.7,
            "max_distance_km": 50,
            "max_price": 200,
        }
        score = compute_matching_score(listing, request)
        assert score["material_compatibility"] == 100.0
        assert score["score"] > 80  # Should be high with exact match

    def test_insufficient_quantity_score(self):
        """Insufficient quantity should lower the score."""
        listing = {
            "material_type": "Bricks",
            "quantity": 100,  # Only 100
            "unit": "pieces",
            "condition": "Good",
            "latitude": 45.5,
            "longitude": -122.7,
            "price": 150,
            "status": "active",
        }
        request = {
            "material_type": "Bricks",
            "quantity_needed": 300,  # Need 300
            "unit": "pieces",
            "min_condition": "Good",
            "latitude": 45.5,
            "longitude": -122.7,
            "max_distance_km": 50,
            "max_price": 200,
        }
        score = compute_matching_score(listing, request)
        assert score["quantity_suitability"] < 100.0

    def test_missing_coordinates_distance_score(self):
        """Missing coordinates should give 0 distance score."""
        listing = {
            "material_type": "Bricks",
            "quantity": 500,
            "unit": "pieces",
            "condition": "Good",
            "latitude": None,
            "longitude": None,
            "price": 150,
            "status": "active",
        }
        request = {
            "material_type": "Bricks",
            "quantity_needed": 300,
            "unit": "pieces",
            "min_condition": "Good",
            "latitude": None,
            "longitude": None,
            "max_distance_km": 50,
            "max_price": 200,
        }
        score = compute_matching_score(listing, request)
        assert score["distance_suitability"] == 0.0

    def test_full_score_with_match(self):
        """All factors aligned should give high total score."""
        listing = {
            "material_type": "Bricks",
            "quantity": 500,
            "unit": "pieces",
            "condition": "Good",
            "latitude": 45.5,
            "longitude": -122.7,
            "price": 100,
            "status": "active",
        }
        request = {
            "material_type": "Bricks",
            "quantity_needed": 300,
            "unit": "pieces",
            "min_condition": "Good",
            "latitude": 45.5,
            "longitude": -122.7,
            "max_distance_km": 50,
            "max_price": 200,
        }
        score = compute_matching_score(listing, request)
        # material=100, quantity=100, condition=100, distance=100 (0km)
        expected = 0.40 * 100 + 0.25 * 100 + 0.20 * 100 + 0.15 * 100
        assert abs(score["score"] - expected) < 0.5


class TestMatchingIntegration:
    """Integration-style tests for matching workflow."""

    def test_eligible_listing_scenario(self):
        """Complete scenario: eligible listing with good match."""
        from database import init_db, get_connection, seed_sample_data

        init_db()
        seed_sample_data()

        conn = get_connection()
        cur = conn.cursor()

        # Get a request and matching listings
        cur.execute("SELECT * FROM requests WHERE id = 1")
        request = dict(cur.fetchone())

        # Get active listings
        cur.execute("SELECT * FROM listings WHERE status = 'active'")
        listings = [dict(row) for row in cur.fetchall()]
        conn.close()

        # Check first listing against request
        if listings:
            listing = listings[0]
            eligible, reason = check_eligibility(listing, request)
            if eligible:
                from matching import compute_matching_score
                score = compute_matching_score(listing, request)
                assert "score" in score
                assert 0 <= score["score"] <= 100
            else:
                # This is expected for some listings
                assert reason is not None

    def test_empty_result_set(self):
        """Test that ineligible listings are properly filtered."""
        # Listing that fails multiple checks
        listing = {
            "material_type": "Plastic",
            "quantity": 10,
            "unit": "pieces",
            "condition": "Poor",
            "latitude": None,
            "longitude": None,
            "price": 500,
            "status": "active",
        }
        request = {
            "material_type": "Bricks",
            "quantity_needed": 100,
            "unit": "pieces",
            "min_condition": "Good",
            "latitude": 45.5,
            "longitude": -122.7,
            "max_distance_km": 10,
            "max_price": 100,
        }
        eligible, reason = check_eligibility(listing, request)
        assert eligible is False
        # Should fail on material mismatch first
        assert reason == "incompatible_material"