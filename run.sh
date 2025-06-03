#!/bin/bash
# Script to run the FastAPI application using uvicorn
uvicorn main:app --host 0.0.0.0 --port 5000 --reload