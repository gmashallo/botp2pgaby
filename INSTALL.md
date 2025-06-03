# Step-by-Step Installation Guide for Binance C2C Trading Platform

This document provides detailed instructions for setting up and running the Binance C2C Trading Platform on your local computer.

## Windows Installation Guide

### 1. Download the Code

1. In Replit, click on the three dots menu in the Files sidebar
2. Select "Download as ZIP"
3. Save the ZIP file to your computer
4. Right-click the ZIP file and select "Extract All..."
5. Choose a destination folder (e.g., `C:\Projects\binance-c2c-bot`)
6. Click "Extract"

### 2. Install Python

1. Go to [python.org/downloads](https://python.org/downloads)
2. Download the latest Python version (3.8 or newer)
3. Run the installer
4. **IMPORTANT**: Check the box "Add Python to PATH"
5. Click "Install Now"
6. Wait for installation to complete
7. Click "Close"

### 3. Open Command Prompt

1. Press `Win + R` on your keyboard
2. Type `cmd` and press Enter
3. This opens the Command Prompt window

### 4. Navigate to Project Folder

```
cd C:\Projects\binance-c2c-bot
```

(Replace with your actual folder path)

### 5. Create Virtual Environment

```
python -m venv venv
```

### 6. Activate Virtual Environment

```
venv\Scripts\activate
```

You should see `(venv)` at the beginning of your command line

### 7. Install Required Packages

```
pip install flask flask-sqlalchemy requests python-dotenv gunicorn jinja2 email-validator fastapi uvicorn pydantic pydantic-settings psycopg2-binary
```

### 8. Create Environment File

1. Open Notepad
2. Paste the following:
```
# Binance API credentials
API_KEY=your_binance_api_key
API_SECRET=your_binance_api_secret

# Proxy Configuration (optional)
PROXY_URL=http://USER796523-ip-154.88.58.248:cc8d8b@global.sta.711proxy.com:30000
```
3. Replace `your_binance_api_key` and `your_binance_api_secret` with your actual Binance API credentials
4. Save the file as `.env` in your project folder
   - In the "Save as" dialog, change "Save as type" to "All Files (*.*)"
   - Enter `.env` as the file name (including the dot)

### 9. Run the Application

```
flask run --host=0.0.0.0 --port=5000
```

### 10. Access the Application

1. Open your web browser
2. Navigate to [http://localhost:5000](http://localhost:5000)

## macOS/Linux Installation Guide

### 1. Download the Code

1. In Replit, click on the three dots menu in the Files sidebar
2. Select "Download as ZIP"
3. Save the ZIP file to your computer
4. Open Terminal
5. Navigate to the download location
6. Extract the ZIP file:
   ```
   unzip binance-c2c-bot.zip -d ~/Projects/
   ```

### 2. Install Python (if not already installed)

#### On macOS:
1. Install Homebrew (if not already installed):
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Install Python:
   ```
   brew install python
   ```

#### On Ubuntu/Debian Linux:
```
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 3. Navigate to Project Folder

```
cd ~/Projects/binance-c2c-bot
```

(Replace with your actual folder path)

### 4. Create Virtual Environment

```
python3 -m venv venv
```

### 5. Activate Virtual Environment

```
source venv/bin/activate
```

You should see `(venv)` at the beginning of your command line

### 6. Install Required Packages

```
pip install flask flask-sqlalchemy requests python-dotenv gunicorn jinja2 email-validator fastapi uvicorn pydantic pydantic-settings psycopg2-binary
```

### 7. Create Environment File

1. Create and open the .env file:
   ```
   nano .env
   ```
2. Paste the following:
   ```
   # Binance API credentials
   API_KEY=your_binance_api_key
   API_SECRET=your_binance_api_secret
   
   # Proxy Configuration (optional)
   PROXY_URL=http://USER796523-ip-154.88.58.248:cc8d8b@global.sta.711proxy.com:30000
   ```
3. Replace `your_binance_api_key` and `your_binance_api_secret` with your actual Binance API credentials
4. Save and exit:
   - Press `Ctrl + X`
   - Press `Y` to confirm
   - Press `Enter` to save

### 8. Make run.sh Executable

```
chmod +x run.sh
```

### 9. Run the Application

```
export FLASK_APP=main.py
flask run --host=0.0.0.0 --port=5000
```

Or use the run script:
```
./run.sh
```

### 10. Access the Application

1. Open your web browser
2. Navigate to [http://localhost:5000](http://localhost:5000)

## Troubleshooting

### Common Issues and Solutions

1. **"'python' is not recognized as an internal or external command"** (Windows):
   - Make sure Python is installed and added to PATH
   - Try using `py` instead of `python`

2. **"ModuleNotFoundError: No module named 'flask'"**:
   - Make sure you've activated the virtual environment
   - Run `pip install flask` to install Flask

3. **"Address already in use"**:
   - Another application is using port 5000
   - Change the port: `flask run --port=5001`

4. **API Connection Errors**:
   - Verify your API key and secret in `.env`
   - Check your internet connection
   - Ensure the proxy configuration is correct

5. **Flask Command Not Found**:
   - On Windows: `python -m flask run --host=0.0.0.0 --port=5000`
   - On macOS/Linux: `python3 -m flask run --host=0.0.0.0 --port=5000`

### Getting Help

If you encounter any issues not covered in this guide:
1. Check the console/terminal for error messages
2. Look for similar issues in the Flask documentation
3. Try searching for the specific error message online
4. Ensure all dependencies are installed correctly