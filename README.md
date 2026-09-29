# CrowdCast
AI-Powered Crowd and Service Management System for FIFA World Cup 2034

# Overview
CrowdCast is a web-based predictive analytics platform designed to support crowd and service management during the FIFA World Cup 2034 in Saudi Arabia. The system focuses on helping restaurants, cafés and nearby services around stadiums manage expected visitor demand by predicting crowd levels and identifying peak hours using machine learning techniques. 

The project addresses the challenge of congestion during large-scale events, where high visitor numbers can lead to long waiting times, inefficient resource allocation and difficulty managing service capacity. CrowdCast provides predictive insights that enable better planning, proactive decision-making and improved visitor experiences. 

# Key Features
Crowd Prediction
The system predicts expected visitor numbers using machine learning models, providing numerical forecasts for service demand at specific times. 
Crowd Level Classification

CrowdCast classifies service demand into three categories:
* High
* Medium
* Low
using a Decision Tree classification model. 

Interactive Dashboard
Prediction results are displayed through an interactive dashboard that provides visualizations, alerts and recommendations for users and staff. 

Synthetic Data Generation
Because real-time restaurant visitor data is not publicly available, the project uses a structured synthetic data generation approach based on geographical information, stadium locations, time factors and behavioral patterns. 

# AI and Data Pipeline
CrowdCast follows a structured data processing pipeline:

1. Data Collection
The project combines:
* Saudi Arabia Points of Interest (POI) data.
* Stadium locations and capacities.
* FIFA World Cup event schedules.

These sources are processed to build a realistic dataset for training machine learning models.

2. Geospatial Processing
The system uses the Haversine Formula to calculate distances between restaurants and stadiums, allowing the system to identify nearby services and filter locations based on distance. 

3. Synthetic Visitor Generation
Visitor numbers are generated using a mathematical simulation engine:
Visitors = Base_Capacity × Time_Factor × Distance_Factor × Weekend_Factor

This approach creates realistic behavioral patterns instead of random values. 

4. Feature Engineering and Data Cleaning
The system improves model performance by:
* Creating meaningful features from raw data.
* Removing statistical outliers using the IQR method.
* Preventing data leakage before training. 

# Machine Learning Models
CrowdCast uses two prediction models:

1. Visitor Count Prediction
Model: Linear Regression

Purpose:
* Predict the expected number of visitors per hour.

2. Crowd Level Prediction
Model: Decision Tree Classifier

Purpose:
* Classify crowd demand into:
High / Medium / Low

# Technologies Used

Backend
* Python 3
* Flask Web Framework
* SQLAlchemy ORM

Database
* MySQL Database

Artificial Intelligence
* Scikit-Learn
* Pandas

Real-Time Communication
* Flask-SocketIO
* WebSockets

Deployment
* Docker
* Docker Compose

# System Architecture
The project follows a structured MVC-based architecture that separates application components and improves maintainability.

Main components include:

```text
app/
├── models.py
├── prediction_engine.py
├── admin/
├── auth/
├── staff/
├── developer/
├── visitor/
└── models/

static/
templates/
scripts/
config.py
run.py
requirements.txt
Dockerfile
docker-compose.yml
```

# Running the Project

Install Requirements
pip install -r requirements.txt

Run with Docker
docker-compose up --build

Docker automatically prepares the environment, installs dependencies, initializes the database and runs the server. 

# Project Objective
CrowdCast aims to provide a smart decision-support system that helps service providers and event organizers anticipate crowd behavior, optimize resource allocation, reduce congestion and improve visitor satisfaction during major international events.

# Conclusion
CrowdCast demonstrates how artificial intelligence and predictive analytics can be used to support crowd management during large-scale events. By combining data processing, machine learning models and an interactive dashboard, the system provides useful predictions that help improve service planning, resource allocation and visitor experience during the FIFA World Cup 2034.
