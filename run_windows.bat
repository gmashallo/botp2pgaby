@echo off
echo Starting Binance C2C Trading Platform...
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found. Please install Python 3.8 or newer.
    echo Visit: https://python.org/downloads
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Error creating virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo Error activating virtual environment.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install flask flask-sqlalchemy requests python-dotenv gunicorn jinja2 email-validator fastapi uvicorn pydantic pydantic-settings psycopg2-binary
if %ERRORLEVEL% NEQ 0 (
    echo Error installing dependencies.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo Warning: .env file not found.
    echo Creating a template .env file. Please update it with your credentials.
    echo # Binance API credentials > .env
    echo API_KEY=your_binance_api_key >> .env
    echo API_SECRET=your_binance_api_secret >> .env
    echo. >> .env
    echo # Proxy Configuration >> .env
    echo PROXY_URL=http://USERNAME:PASSWORD@HOST:PORT >> .env
)

REM Start the application
echo.
echo Starting Flask application...
echo Navigate to http://localhost:5000 in your web browser
echo Press Ctrl+C to stop the server
echo.
python -m flask run --host=0.0.0.0 --port=5000

REM Deactivate virtual environment
call venv\Scripts\deactivate

pause