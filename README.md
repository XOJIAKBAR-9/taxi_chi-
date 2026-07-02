🚕 TaxiChi - Regional Ride-Sharing Platform

TaxiChi is a modern, specialized ride-sharing platform engineered specifically for inter-provincial and regional travel within Uzbekistan.
While typical ride-hailing apps focus on short, intra-city trips, TaxiChi is designed to connect passengers and drivers for long-haul journeys (e.g., Fergana to Tashkent). It handles the unique complexities of regional transport, including seat-based booking, vehicle class separation, and automated driver verification.

🌟 Key Features

For Passengers
Regional Routing: Book trips across all 14 administrative regions of Uzbekistan using a clean, text-based choice system.
Seat-Based Booking: Reserve specific seats (Front, Back) rather than booking the entire vehicle.
Smart Payments: Flexible payment configuration allowing default choices between Cash, Payme, and Click.
Integrated Comms: Attach an initial message directly to your booking request to instantly spin up a chat with your driver.

For Drivers
Fleet Management Hub: A dedicated Driver Profile dashboard to manage vehicle details (e.g., Chevrolet Cobalt, Plate Number).
Automated Document Verification: Upload Tech Passports and Driver's Licenses for automated, real-time OCR/KYC review.
Online/Offline Toggles: Explicit control over availability to prevent system manipulation.
Ride Analytics: Track total rides, acceptance rates, and earnings.

Security & Architecture
Strict Role Separation: Built-in Django permissions (IsPassengerOnly, IsDriver) prevent malicious actions, such as drivers booking fake rides to manipulate surge pricing.
Real-time Ready: Foundation laid for ASGI/Channels integration to support live map tracking and WebSocket-based chat.

🛠 Tech Stack
Backend
Python 3.x
Django & Django REST Framework (DRF)
Simple JWT (Authentication)
SQLite (Dev) / PostgreSQL (Prod ready)
DRF Spectacular (OpenAPI 3 Schema Generation)
Frontend (Demo)
React.js
Tailwind CSS
Lucide Icons

🚀 Quick Start (Local Development)

1. Clone the Repository
   git clone https://github.com/yourusername/taxi_chi.git
   cd taxi_chi

2. Set up the Python Environment
   python -m venv venv
   source venv/bin/activate # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt

3. Environment Variables
   Create a .env file in the root directory (use .env.example as a template).
   DEBUG=True
   SECRET_KEY=your_secret_key_here

4. Database Migrations
   python manage.py makemigrations
   python manage.py migrate

5. Run the Server
   python manage.py runserver
   The API will be available at http://127.0.0.1:8000/api/.

📖 API Documentation
TaxiChi uses drf-spectacular for auto-generated API documentation. Once the server is running, you can explore the endpoints via:
Swagger UI: http://127.0.0.1:8000/api/schema/swagger-ui/
Redoc: http://127.0.0.1:8000/api/schema/redoc/

🛣 Roadmap
[ ] Migrate from WSGI to ASGI (Django Channels) for WebSocket support.
[ ] Implement live GPS coordinate broadcasting (LocationViewSet).
[ ] Connect the mock OCR function (verify_document_with_ocr) to a live provider (Google Cloud Vision / Veriff).
[ ] Add deep-link invoice generation for Payme/Click checkouts.
Built for the roads of Uzbekistan. 🇺🇿
