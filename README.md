# Binance C2C Trading Bot

A Flask-based trading bot for Binance C2C (P2P) markets with machine learning price analysis.

## Features

- Real-time USDT/TZS price monitoring
- Machine learning-based ad filtering
- Automatic price updates
- Trader leaderboard analysis
- Ad posting and order management
- Blacklist management for ads and advertisers

## Quick Setup

1. Configure environment variables:
   - `API_KEY`: Your Binance API key
   - `API_SECRET`: Your Binance API secret

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   gunicorn --bind 0.0.0.0:5000 main:app
   ```

## Deployment

This bot is configured for deployment on DigitalOcean App Platform in Singapore region to bypass geographical restrictions.

## Environment Variables

Required:
- `API_KEY`: Binance API key with C2C trading permissions
- `API_SECRET`: Binance API secret

Optional:
- `SESSION_SECRET`: Flask session secret (auto-generated if not provided)

## API Endpoints

- `GET /` - Web interface
- `GET /api/top-price` - Get top market prices
- `POST /api/post-ad` - Create new trading ad
- `POST /api/release-order` - Release crypto after payment
- `GET /api/leaderboard` - Top traders analysis
- Price updater controls and filter management endpoints

## Regional Requirements

Deploy in Singapore or other Binance-supported regions for full API access.