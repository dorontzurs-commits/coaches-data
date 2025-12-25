# Deployment Guide - Render.com

## Architecture Decision

**We use SEPARATE services for Backend and Frontend:**
- Backend: Web Service (Python/Flask)
- Frontend: Static Site (React/Vite)

This separation allows for:
- Independent scaling
- Separate deployments
- Better resource management
- Clear separation of concerns

## Backend Service Configuration

**Service Type:** Web Service  
**Name:** `coach-scraper-api` (or `coaches-data`)

**Settings:**
- **Language:** Python 3
- **Branch:** `main`
- **Root Directory:** (empty or `backend`)
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `cd backend && python app.py`
- **Region:** Oregon (US West) or your preferred region

**Environment Variables:**
- `PORT` - Automatically set by Render (no need to add manually)
- `PYTHON_VERSION` - Optional, defaults to latest

**Health Check:**
- Path: `/api/status`

## Frontend Service Configuration

**Service Type:** Static Site  
**Name:** `coach-scraper-frontend`

**Settings:**
- **Branch:** `main`
- **Root Directory:** (empty)
- **Build Command:** `cd frontend && npm install && npm run build`
- **Publish Directory:** `frontend/dist`

**Environment Variables:**
- `VITE_API_BASE_URL` - **REQUIRED**: Set to your backend service URL
  - Example: `https://coach-scraper-api.onrender.com/api`
  - **Important:** Update this after backend is deployed!

## Deployment Steps

1. **Deploy Backend:**
   - Create new Web Service in Render
   - Connect GitHub repository: `dorontzurs-commits/coaches-data`
   - Configure as described above
   - Wait for deployment to complete
   - Copy the service URL

2. **Deploy Frontend:**
   - Create new Static Site in Render
   - Connect same GitHub repository
   - Configure as described above
   - **Add Environment Variable:**
     - Key: `VITE_API_BASE_URL`
     - Value: `https://[your-backend-url].onrender.com/api`
   - Deploy

3. **Verify:**
   - Check backend health: `https://[backend-url]/api/status`
   - Open frontend URL and test the application

## Repository Structure

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
│   ├── public/
│   │   └── logo.png        # Logo file
│   └── dist/               # Built files (generated, not in git)
├── requirements.txt        # Python dependencies
├── render.yaml             # Render Blueprint (optional)
└── README.md               # Project documentation
```

## Important Notes

- The frontend uses `VITE_API_BASE_URL` environment variable to connect to backend
- Backend runs on port set by Render (read from `PORT` env var)
- Both services are deployed from the same repository
- Frontend build happens during deployment, output goes to `frontend/dist`
- Logo is served from `frontend/public/logo.png`

## Troubleshooting

**Backend not accessible:**
- Check health endpoint: `/api/status`
- Verify CORS is enabled in Flask
- Check Render logs for errors

**Frontend can't connect to backend:**
- Verify `VITE_API_BASE_URL` is set correctly
- Check that backend URL includes `/api` at the end
- Rebuild frontend after changing environment variable

**Build failures:**
- Check Render build logs
- Verify all dependencies are in `requirements.txt` and `package.json`
- Ensure build commands are correct





