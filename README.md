# Binance C2C Trading Platform

A Flask-powered C2C trading platform for USDT/TZS transactions, providing comprehensive trading tools and real-time market insights.

## Features

- Binance C2C API integration
- Top ad price retrieval
- Order matching and release
- Trader leaderboard
- Simple HTML dashboard for trading operations
- Automatic price updater with machine learning capabilities
- Bot detection and filtering
- Intelligent price adjustment
- Direct API connection (no proxy required)

## Installation Guide

### Prerequisites

- Python 3.8 or newer
- Binance API key with C2C trading permissions
- Internet connection from a Binance-supported region (or VPN)

### Step 1: Clone/Download the Code

Download this repository to your local machine.

### Step 2: Setup Python Environment

```bash
# Navigate to the project folder
cd path/to/binance-c2c-bot

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install flask flask-sqlalchemy requests python-dotenv gunicorn jinja2 email-validator fastapi uvicorn pydantic pydantic-settings psycopg2-binary scikit-learn numpy pandas joblib
```

### Step 4: Create Environment Variables

Create a `.env` file in the root directory with the following content:

```
# Binance API credentials
API_KEY=your_binance_api_key
API_SECRET=your_binance_api_secret

# No proxy needed - direct connection is used
```

Replace the placeholders with your actual credentials.

### Step 5: Run the Application

```bash
# Using Flask's development server
# On Windows:
flask run --host=0.0.0.0 --port=5000
# On macOS/Linux:
FLASK_APP=main.py flask run --host=0.0.0.0 --port=5000

# OR using Gunicorn (for production - Linux/macOS only)
gunicorn --bind 0.0.0.0:5000 main:app

# For Windows production, install waitress:
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 main:app
```

### Step 6: Access the Application

Open your web browser and navigate to:
```
http://localhost:5000
```

## API Endpoints

- `/api/top-price` - Get top USDT/TZS prices
- `/api/release-order` - Release crypto after confirmed payment
- `/api/post-ad` - Create a new C2C ad
- `/api/leaderboard` - View top traders by volume/orders
- `/api/price-updater/status` - Check price updater status
- `/api/price-updater/start` - Start price updater
- `/api/price-updater/stop` - Stop price updater

## Troubleshooting

1. **"ModuleNotFoundError"**: Make sure you've installed all dependencies with pip
2. **API Connection Errors**: Verify your API key and secret in the `.env` file
3. **Location Restrictions**: If you receive location restriction errors from Binance, you may need to use a VPN from a supported country
4. **Port Already in Use**: Change the port number in the run command (e.g., `--port=5001`)
5. **Flask Command Not Found**: Make sure the virtual environment is activated
6. **ML Model Errors**: If you experience ML-related errors, delete the `models/` directory and let the system rebuild the models

## Machine Learning Features

This application uses machine learning algorithms to optimize your C2C trading:

1. **Bot Detection**: Our system automatically identifies and filters out advertisers that show bot-like behavior, ensuring you're only competing with legitimate traders.

2. **Restricted Advertiser Filtering**: You can blacklist specific advertisers, and the system will automatically exclude them from price calculations.

3. **Intelligent Price Adjustment**: Instead of simple percentage-based adjustments, the system analyzes market data and recommends optimal pricing strategies.

4. **Anomaly Detection**: Using Isolation Forest algorithm, the system identifies and ignores unusual pricing patterns that might distort the market.

5. **Adaptive Learning**: The ML model improves over time as it collects more data on trading patterns.

## Notes

- This application now uses direct connection to Binance API (no proxy required).
- For the application to work properly, you need valid Binance API keys with C2C trading permissions.
- Keep your API keys secure and never share them. The `.env` file should not be committed to version control.
- The ML models are stored in the `models/` directory and will be created automatically on first run.