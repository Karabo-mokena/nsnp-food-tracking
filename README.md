# NSNP Food Distribution and Tracking System

**Module:** NPRT63 — Project  
**Phase:** 4 — Implementation & Presentation  
**Institution:** Sol Plaatje University  
**Team:** Karabo Mokoena, Karabo Molomo, Kamohelo Thabethe, Henderson Thuto  

---

## Overview

A web-based system for tracking food deliveries, managing school inventories,
and monitoring the National School Nutrition Programme (NSNP) across South
African schools. Supports three user roles: Delivery Driver, School Staff,
and Nutrition Programme Manager.

---

## Features

- Role-based authentication and dashboards
- Delivery logging and tracking
- Inventory management with low-stock alerts
- Issue reporting with file attachments
- Real-time notifications
- Report generation (PDF, Excel, CSV)
- User management with approval workflow

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 6.x |
| Language | Python 3.11+ |
| Database | SQLite (prototype) |
| Frontend | HTML, CSS, Bootstrap Icons |
| Charts | Chart.js |
| Reports | reportlab, openpyxl |

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Karabo-mokena/nsnp-food-tracking.git
cd nsnp-food-tracking

# Install dependencies
pip install django openpyxl reportlab

# Apply database migrations
python manage.py migrate

# Create an admin account
python manage.py createsuperuser

# Start the development server
python manage.py runserver
