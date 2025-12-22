# Coach Scraper

A web application for scraping coach career history from Transfermarkt.

## Setup for Render

### Backend Setup (Web Service)

1. Go to Render Dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository: `https://github.com/dorontzurs-commits/coaches-data`
4. Configure:
   - **Name**: `coach-scraper-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && python app.py`
   - **Environment Variables**:
     - `PORT`: `10000` (Render will set this automatically, but you can specify)
     - `PYTHON_VERSION`: `3.11.0`

### Frontend Setup (Static Site)

1. Go to Render Dashboard
2. Click "New +" → "Static Site"
3. Connect your GitHub repository: `https://github.com/dorontzurs-commits/coaches-data`
4. Configure:
   - **Name**: `coach-scraper-frontend`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist`
   - **Environment Variables**:
     - `VITE_API_BASE_URL`: `https://coach-scraper-api.onrender.com/api` (replace with your actual backend URL)

### Alternative: Using render.yaml

If you prefer, you can use the `render.yaml` file included in the repository. Render will automatically detect it and create both services.

## Local Development

### Backend
```bash
cd backend
python app.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
Coach/
├── backend/
│   ├── app.py              # Flask API server
│   └── scraper/
│       └── scraper.py      # Web scraping logic
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React component
│   │   └── index.css       # Styles
│   └── dist/               # Built files (generated)
└── requirements.txt        # Python dependencies
```

## Features

- Scrape coach data from multiple continents (Europe, America, Africa, Asia)
- Select multiple leagues and clubs
- Export results to Excel with separate sheets per league
- Beautiful UI with react-select dropdowns
