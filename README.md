# ReBuild AI - Construction Material Reuse Platform

## Overview
ReBuild AI is an intelligent construction-material reuse platform that connects people who have surplus construction materials with people who need them. The platform uses AI image recognition combined with location-aware material matching to facilitate reuse.

## Problem Statement
Construction sites, renovation projects, and demolition activities generate reusable materials such as bricks, timber, tiles, metal, doors, windows, and fixtures. These materials are often discarded because nearby people who need them cannot discover them.

## Features
- **List Materials**: Upload surplus materials with AI-suggested categorization
- **Find Materials**: Search for materials by category, quantity, condition, and location
- **My Listings & Enquiries**: Manage your listings and track enquiries
- **Impact Dashboard**: View statistics and charts on reuse activity
- **AI Image Classification**: CLIP-based material categorization from photographs
- **Intelligent Matching**: Score-based matching with transparent factor breakdown
- **Demo User Workflow**: Test without authentication using fictional users

## Architecture
- **Streamlit**: Web interface with sidebar navigation
- **SQLite**: Local persistent database (`database.db`)
- **CLIP Model**: Hugging Face `openai/clip-vit-large-patch14` for image classification
- **Custom Matching Engine**: Multi-factor scoring system (material, quantity, condition, distance)

## Database Schema
- **users**: id, name, role, organization, email, created_at
- **listings**: id, supplier_id, title, description, material_type, quantity, unit, condition, image_path, location_text, latitude, longitude, price, status, created_at, updated_at
- **requests**: id, recipient_id, material_type, quantity_needed, unit, min_condition, location_text, latitude, longitude, max_distance_km, max_price, status, created_at, updated_at
- **enquiries**: id, listing_id, request_id, supplier_id, recipient_id, message, status, quantity_reused, updated_at, completed_at

## Installation

### Windows
```powershell
# 1. Clone the repository
git clone https://github.com/yourusername/rebuild-ai.git
cd rebuild-ai

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Run the application
streamlit run app.py
```

### Linux / macOS
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/rebuild-ai.git
cd rebuild-ai

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
streamlit run app.py
```

## Virtual Environment Setup
```powershell
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

## Running Tests
```powershell
# From the project root
pytest tests/
```

## Sample Data
To seed the database with fictional test data:
```powershell
python sample_data.py
# Or from Python
import sample_data
sample_data.seed_if_empty()
```

## Streamlit Community Cloud Deployment
1. Push this repository to GitHub
2. Create a new app on Streamlit Community Cloud
3. Set the main file path to `app.py`
4. Note: Ephemeral storage may not persist data between restarts. For production, use a managed database (PostgreSQL) and object storage (S3) for uploads.

## Limitations & Future Improvements
- Image classification is AI suggestion only - supplier must confirm
- Matching uses Euclidean/Haversine distance with available coordinates only
- Unit conversions limited - exact unit matches preferred
- No user authentication in MVP - uses demo user selector
- Carbon savings not claimed without defensible calculation method
- Future: user authentication, managed database, object storage integration, trained model fine-tuning