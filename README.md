# Gram Vaani - AI Voice Assistant for Rural India

## 🌾 Bridging the Digital Dialect Divide

Gram Vaani is a lightweight, AI-powered voice assistant designed specifically for rural Indian users. It understands local dialects, provides real-time information about weather, crop prices, and government schemes, and responds in a voice format that users can easily understand.

## 🎯 Problem Statement

In rapidly digitizing India, access to information is still a privilege of those who speak mainstream languages. For millions in rural areas, local dialects are the primary mode of communication, creating a "digital dialect divide." This linguistic barrier excludes them from critical information about:

- Weather forecasts that affect their crops
- Real-time market prices for their produce  
- Vital health services
- Essential government schemes designed for their benefit

## 🚀 Solution

Gram Vaani acts as a bridge, not a barrier:

- **It Listens**: Understands native dialects using OpenAI's Whisper
- **It Understands**: Uses GPT-4's advanced reasoning to grasp user intent
- **It Informs**: Fetches live, relevant information from reliable sources
- **It Responds**: Provides clear answers in voice and text format

## 🏗️ System Architecture

```
User → Frontend (React) → Backend (FastAPI) → AI Services (OpenAI)
                                    ↓
                            External APIs (Weather, Markets)
                                    ↓
                            Local Database (Govt Schemes)
```

## 🛠️ Tech Stack

- **Frontend**: React + Vite
- **Backend**: Python + FastAPI
- **ASR**: OpenAI Whisper API
- **NLU**: OpenAI GPT-4 API
- **TTS**: OpenAI TTS API
- **Data Sources**: OpenWeatherMap, Government APIs, Local Database

## 🚀 Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 📱 Features

- Multi-dialect voice recognition
- Real-time weather information
- Crop price updates
- Government scheme information
- Offline-capable design
- Mobile-first interface

## 🏆 Built for OpenAI X NXT Buildathon

This project addresses the critical need for inclusive AI technology in rural India, ensuring that language barriers don't prevent access to essential information and services.
# ruralai
