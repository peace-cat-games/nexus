# Nexus Web

A web-based interface for playing the Nexus board game, with a FastAPI backend and React frontend.

## Overview

This package provides a full-stack web application for the Nexus game:

- **Backend**: FastAPI REST API serving game logic
- **Frontend**: React + TypeScript UI with Vite

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm

## Project Structure

```
nexus-web/
├── backend/
│   ├── main.py           # FastAPI application
│   └── requirements.txt  # Python dependencies
└── frontend/
    ├── src/
    │   ├── api/          # API client
    │   ├── components/   # React components
    │   ├── App.tsx       # Main app component
    │   └── types.ts      # TypeScript types
    ├── package.json
    └── vite.config.ts
```

## Installation

### Backend

```bash
cd backend
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Running the Application

### Start the Backend

```bash
cd backend
python main.py
# Or with uvicorn directly:
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### Start the Frontend

```bash
cd frontend
npm run dev
```

The UI will be available at `http://localhost:5173`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/games` | Create a new game |
| `GET` | `/api/games/{game_id}` | Get game state |
| `POST` | `/api/games/{game_id}/move` | Make a move |
| `GET` | `/api/games/{game_id}/debt-resolution` | Get debt resolution info |
| `DELETE` | `/api/games/{game_id}` | Delete a game |
| `GET` | `/api/health` | Health check |

### Create Game Request

```json
{
  "size": 5,
  "p1": 2,
  "p2": 4
}
```

### Make Move Request

```json
{
  "row": 2,
  "col": 3,
  "stones_to_remove": [[0, 0], [1, 1]]
}
```

## Testing

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm test
```

## Development

### Linting (Frontend)

```bash
cd frontend
npm run lint
```

### Build (Frontend)

```bash
cd frontend
npm run build
```
