# Coach Scraper

A web application for scraping coach career history from Transfermarkt.

## Deployment to Render.com

**Architecture:** We use **SEPARATE services** for Backend and Frontend.

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions and configuration.

### Quick Setup:

1. **Backend (Web Service):**
   - Build: `pip install -r requirements.txt`
   - Start: `cd backend && python app.py`

2. **Frontend (Static Site):**
   - Build: `cd frontend && npm install && npm run build`
   - Publish: `frontend/dist`
   - **Required Env Var:** `VITE_API_BASE_URL` = your backend URL + `/api`

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
