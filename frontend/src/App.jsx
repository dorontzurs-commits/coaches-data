import React, { useState, useEffect } from 'react'
import axios from 'axios'
import * as XLSX from 'xlsx'
import Select from 'react-select'
import './index.css'

function App() {
  const [status, setStatus] = useState({
    running: false,
    progress: {
      current: 0,
      total: 0,
      current_club: '',
      status: 'idle'
    }
  })
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [continents] = useState([
    { value: 'europa', label: 'Europe' },
    { value: 'amerika', label: 'America' },
    { value: 'afrika', label: 'Africa' },
    { value: 'asien', label: 'Asia' }
  ])
  const [selectedContinent, setSelectedContinent] = useState('')
  const [leagues, setLeagues] = useState([])
  const [selectedLeagues, setSelectedLeagues] = useState([])
  const [clubs, setClubs] = useState([])
  const [selectedClubs, setSelectedClubs] = useState([])
  const [loadingLeagues, setLoadingLeagues] = useState(false)
  const [loadingClubs, setLoadingClubs] = useState(false)
  const [showAnimation, setShowAnimation] = useState(false)

  const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

  // Fetch leagues when continent is selected
  useEffect(() => {
    if (selectedContinent) {
      const fetchLeagues = async () => {
        setLoadingLeagues(true)
        setLeagues([])
        setSelectedLeagues([])
        setClubs([])
        setSelectedClubs([])
        setError(null)
        try {
          const response = await axios.get(`${API_BASE}/leagues?continent=${selectedContinent}`)
          setLeagues(response.data)
          if (response.data.length === 0) {
            setError('No leagues found for this continent')
          }
        } catch (err) {
          console.error('Error fetching leagues:', err)
          setError('Failed to load leagues')
        } finally {
          setLoadingLeagues(false)
        }
      }
      fetchLeagues()
    } else {
      setLeagues([])
      setSelectedLeagues([])
      setClubs([])
      setSelectedClubs([])
    }
  }, [selectedContinent])

  // Fetch clubs when leagues are selected
  useEffect(() => {
    if (selectedLeagues.length > 0) {
      const fetchClubs = async () => {
        setLoadingClubs(true)
        setClubs([])
        setSelectedClubs([])
        setError(null) // Clear previous errors
        try {
          // Fetch clubs from all selected leagues
          const allClubs = []
          const clubPromises = selectedLeagues.map(async (leagueId) => {
            const league = leagues.find(l => l.id === leagueId || l.url === leagueId)
            if (league) {
              console.log('Fetching clubs for league:', league.name, league.url)
              const response = await axios.post(`${API_BASE}/clubs`, {
                league_url: league.url
              })
              // Add league info to each club
              return response.data.map(club => ({
                ...club,
                leagueName: league.name,
                leagueId: league.id || league.url
              }))
            }
            return []
          })
          
          const clubsArrays = await Promise.all(clubPromises)
          const mergedClubs = clubsArrays.flat()
          
          console.log('Received clubs:', mergedClubs.length)
          setClubs(mergedClubs)
          if (mergedClubs.length === 0) {
            setError('No clubs found for selected leagues')
          }
        } catch (err) {
          console.error('Error fetching clubs:', err)
          const errorMsg = err.response?.data?.error || err.message || 'Failed to load clubs'
          setError(`Failed to load clubs: ${errorMsg}`)
        } finally {
          setLoadingClubs(false)
        }
      }
      fetchClubs()
    } else {
      setClubs([])
      setSelectedClubs([])
    }
  }, [selectedLeagues, leagues])

  // Poll for status updates
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE}/status`)
        setStatus(response.data)
        
        // Update results if available
        if (response.data.results && response.data.results.length > 0) {
          setResults(response.data.results)
        }
      } catch (err) {
        console.error('Error fetching status:', err)
      }
    }, 1000) // Poll every second

    return () => clearInterval(interval)
  }, [])

  const startScraper = async () => {
    setLoading(true)
    setError(null)
    setResults([])
    setShowAnimation(true) // הפעל אנימציה
    
    // עצור את האנימציה אחרי 3 שניות
    setTimeout(() => {
      setShowAnimation(false)
    }, 3000)
    
    try {
      // If specific clubs are selected, use multiple clubs scraper
      if (selectedClubs.length > 0) {
        if (selectedClubs.length === 1) {
          // Single club - use existing endpoint
          const club = selectedClubs[0]
          await axios.post(`${API_BASE}/start-club`, {
            club_url: club.url,
            club_name: club.name
          })
        } else {
          // Multiple clubs - send array
          await axios.post(`${API_BASE}/start-clubs`, {
            clubs: selectedClubs.map(club => ({
              url: club.url,
              name: club.name
            }))
          })
        }
      } else if (selectedLeagues.length > 0) {
        // If leagues are selected (but no specific club), scrape all clubs from those leagues
        const selectedLeagueObjects = selectedLeagues.map(leagueId => 
          leagues.find(l => l.id === leagueId || l.url === leagueId)
        ).filter(Boolean)
        
        if (selectedLeagueObjects.length > 0) {
          // If only one league selected, use the single league endpoint
          if (selectedLeagueObjects.length === 1) {
            const league = selectedLeagueObjects[0]
            await axios.post(`${API_BASE}/start`, {
              league_url: league.url,
              league_name: league.name
            })
          } else {
            // Multiple leagues - send array of league URLs
            await axios.post(`${API_BASE}/start`, {
              league_urls: selectedLeagueObjects.map(l => ({ url: l.url, name: l.name }))
            })
          }
        }
      } else if (selectedContinent) {
        // If a continent is selected (but no specific league), scrape all leagues from that continent
        await axios.post(`${API_BASE}/start`, {
          continent: selectedContinent
        })
      } else {
        // Otherwise, run full scraper on all clubs from all leagues (default: Europa)
        await axios.post(`${API_BASE}/start`)
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start scraper')
      setLoading(false)
      setShowAnimation(false) // עצור אנימציה במקרה של שגיאה
    }
  }

  const stopScraper = async () => {
    try {
      await axios.post(`${API_BASE}/stop`)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to stop scraper')
    }
  }

  const resetScraper = async () => {
    try {
      await axios.post(`${API_BASE}/reset`)
      
      // Reset all state to default values
      setResults([])
      setError(null)
      setLoading(false)
      setShowAnimation(false)
      
      // Reset all selections
      setSelectedContinent('')
      setSelectedLeagues([])
      setSelectedClubs([])
      
      // Clear loaded data
      setLeagues([])
      setClubs([])
      
      // Reset status to default
      setStatus({
        running: false,
        progress: {
          current: 0,
          total: 0,
          current_club: '',
          status: 'idle'
        }
      })
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to reset scraper')
    }
  }

  const exportToExcel = () => {
    if (results.length === 0) {
      alert('No results to export')
      return
    }

    // Group results by league
    const resultsByLeague = {}
    results.forEach(row => {
      const leagueName = row.league || 'Unknown League'
      if (!resultsByLeague[leagueName]) {
        resultsByLeague[leagueName] = []
      }
      resultsByLeague[leagueName].push(row)
    })

    // Create a new workbook
    const workbook = XLSX.utils.book_new()

    // Create a sheet for each league
    Object.keys(resultsByLeague).forEach(leagueName => {
      const leagueResults = resultsByLeague[leagueName]
      
      // Headers (without League column)
      const headers = [
        'League Country', 'Current Club', 'Current Club URL', 
        'Manager', 'Manager Role', 'Manager ID',
        'History Club', 'History Club URL', 'Role', 
        'Appointed Season', 'Appointed Date', 'Until Season', 'Until Date',
        'Period From', 'Period Until', 'Days in Charge',
        'Matches', 'Wins', 'Draws', 'Losses', 'Players Used',
        'Avg Goals For', 'Avg Goals Against', 'Points Per Match'
      ]
      
      // Convert data to array format
      const data = [
        headers,
        ...leagueResults.map(row => [
          row.league_country || '',
          row.current_club || '',
          row.current_club_url || '',
          row.manager || '',
          row.manager_role || 'Manager',
          row.manager_id || '',
          row.history_club || '',
          row.history_club_url || '',
          row.role || '',
          row.appointed_season || '',
          row.appointed_date || '',
          row.until_season || '',
          row.until_date || '',
          row.period_from || '',
          row.period_until || '',
          row.days_in_charge || '',
          row.matches || '',
          row.wins || '',
          row.draws || '',
          row.losses || '',
          row.players_used || '',
          row.avg_goals_for || '',
          row.avg_goals_against || '',
          row.points_per_match || ''
        ])
      ]
      
      // Create worksheet
      const worksheet = XLSX.utils.aoa_to_sheet(data)
      
      // Add worksheet to workbook with league name as sheet name
      // Excel sheet names are limited to 31 characters and cannot contain certain characters
      let sheetName = leagueName
        .replace(/[\\\/\?\*\[\]:]/g, '_') // Replace invalid characters
        .substring(0, 31) // Limit to 31 characters
      
      // Ensure sheet name is not empty
      if (!sheetName) {
        sheetName = 'Sheet'
      }
      
      XLSX.utils.book_append_sheet(workbook, worksheet, sheetName)
    })

    // Write file
    const fileName = `coach_achievements_${new Date().toISOString().split('T')[0]}.xlsx`
    XLSX.writeFile(workbook, fileName)
  }

  const progressPercentage = status.progress.total > 0 
    ? Math.round((status.progress.current / status.progress.total) * 100) 
    : 0

  return (
    <div className="container">
      <div className="header">
        <div className="logo-container">
          <img src="/logo.png" alt="Logo" className={`logo ${status.running ? 'logo-running' : ''}`} />
          <p>
            {status.running ? (
              <span className="running-message">
                <strong>NNNUUU...</strong> Another operation is currently running. Please wait for it to complete.
              </span>
            ) : (
              <>
                <strong>NNNUUUU...</strong> Extract coach career history from top football clubs
              </>
            )}
          </p>
        </div>
      </div>

      <div className="controls">
        <div className="selection-section">
          <div className="select-group">
            <label htmlFor="continent-select">Select Continent:</label>
            <Select
              id="continent-select"
              value={continents.find(c => c.value === selectedContinent) || null}
              onChange={(option) => setSelectedContinent(option ? option.value : '')}
              options={continents}
              isDisabled={status.running}
              placeholder="-- Select a Continent --"
              isClearable
              className="react-select-container"
              classNamePrefix="react-select"
            />
          </div>

          {selectedContinent && (
            <div className="select-group">
              <label htmlFor="league-select">Select League(s):</label>
              <Select
                id="league-select"
                isMulti
                value={leagues.filter(l => selectedLeagues.includes(l.id || l.url)).map(l => ({
                  value: l.id || l.url,
                  label: `${l.name}${l.country ? ` (${l.country})` : ''}`
                }))}
                onChange={(selected) => {
                  setSelectedLeagues(selected ? selected.map(s => s.value) : [])
                }}
                options={leagues.map(league => ({
                  value: league.id || league.url,
                  label: `${league.name}${league.country ? ` (${league.country})` : ''}`
                }))}
                isDisabled={status.running || loadingLeagues}
                placeholder={loadingLeagues ? "Loading leagues..." : "-- Select League(s) --"}
                isClearable
                closeMenuOnSelect={false}
                className="react-select-container"
                classNamePrefix="react-select"
              />
            </div>
          )}

          {selectedLeagues.length > 0 && (
            <div className="select-group">
              <label htmlFor="club-select">Select Club(s):</label>
              <Select
                id="club-select"
                isMulti
                value={clubs.filter(c => selectedClubs.some(sc => sc.url === c.url)).map(club => ({
                  value: club.url,
                  label: `${club.name}${club.leagueName ? ` (${club.leagueName})` : ''}`
                }))}
                onChange={(selected) => {
                  const selectedClubObjects = selected ? selected.map(s => {
                    const club = clubs.find(c => c.url === s.value)
                    return club
                  }).filter(Boolean) : []
                  setSelectedClubs(selectedClubObjects)
                }}
                options={clubs.map(club => ({
                  value: club.url,
                  label: `${club.name}${club.leagueName ? ` (${club.leagueName})` : ''}`
                }))}
                isDisabled={status.running || loadingClubs}
                placeholder={loadingClubs ? "Loading clubs..." : "-- Select Club(s) --"}
                isClearable
                closeMenuOnSelect={false}
                className="react-select-container"
                classNamePrefix="react-select"
              />
            </div>
          )}
        </div>

        <div className="button-group">
          <button 
            className="btn btn-primary" 
            onClick={startScraper} 
            disabled={status.running || loading || (selectedClubs.length === 0 && selectedLeagues.length === 0 && !selectedContinent)}
            title={selectedClubs.length > 0 ? `Scrape ${selectedClubs.length} selected club(s)` : selectedLeagues.length > 0 ? `Scrape all clubs from ${selectedLeagues.length} selected league(s)` : selectedContinent ? `Scrape all leagues from ${continents.find(c => c.value === selectedContinent)?.label}` : 'Select a continent, league(s) or club(s) first'}
          >
            ▶ {selectedClubs.length > 0 ? `Start Scraper (${selectedClubs.length} Club${selectedClubs.length > 1 ? 's' : ''})` : selectedLeagues.length > 0 ? `Start Scraper (${selectedLeagues.length} League${selectedLeagues.length > 1 ? 's' : ''})` : selectedContinent ? `Start Scraper (All Leagues - ${continents.find(c => c.value === selectedContinent)?.label})` : 'Start Scraper'}
          </button>
          <button 
            className="btn btn-danger" 
            onClick={stopScraper} 
            disabled={!status.running}
          >
            ⏹ Stop Scraper
          </button>
          <button 
            className="btn btn-secondary" 
            onClick={resetScraper} 
            disabled={status.running}
          >
            🔄 Reset
          </button>
          {results.length > 0 && (
            <button 
              className="btn btn-success" 
              onClick={exportToExcel}
            >
              💾 Export to Excel
            </button>
          )}
        </div>

        {error && (
          <div className="error">
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      <div className="progress-section">
        <h2>Progress</h2>
        <div className="status-text">
          <strong>Status:</strong> {status.progress.status || 'idle'}
        </div>
        {status.progress.current_club && (
          <div className="status-text">
            <strong>Current Club:</strong> {status.progress.current_club}
          </div>
        )}
        {status.progress.total > 0 && (
          <>
            <div className="status-text">
              <strong>Progress:</strong> {status.progress.current} / {status.progress.total} clubs
            </div>
            <div className="progress-bar-container">
              <div 
                className="progress-bar" 
                style={{ width: `${progressPercentage}%` }}
              >
                {progressPercentage}%
              </div>
            </div>
          </>
        )}
      </div>

      <div className="results-section">
        <div className="results-header">
          <h2>Results</h2>
          {results.length > 0 && (
            <span style={{ color: '#94a3b8', fontSize: '1rem' }}>
              {results.length} career entr{results.length !== 1 ? 'ies' : 'y'} found
            </span>
          )}
        </div>

        {status.running && results.length === 0 && (
          <div className="loading">
            <p>⏳ Scraping in progress... Please wait...</p>
          </div>
        )}

        {!status.running && results.length === 0 && status.progress.status === 'idle' && (
          <div className="empty-state">
            <h3>No results yet</h3>
            <p>Click "Start Scraper" to begin extracting coach career history</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Current Club</th>
                  <th>Manager</th>
                  <th>Manager ID</th>
                  <th>History Club</th>
                  <th>Role</th>
                  <th>Appointed Season</th>
                  <th>Appointed Date</th>
                  <th>Until Season</th>
                  <th>Until Date</th>
                  <th>Period From</th>
                  <th>Period Until</th>
                  <th>Days in Charge</th>
                  <th>Matches</th>
                  <th>Wins</th>
                  <th>Draws</th>
                  <th>Losses</th>
                  <th>Players Used</th>
                  <th>Avg Goals For</th>
                  <th>Avg Goals Against</th>
                  <th>Points Per Match</th>
                </tr>
              </thead>
              <tbody>
                {results.map((row, index) => (
                  <tr key={index}>
                    <td>{row.current_club}</td>
                    <td>{row.manager}</td>
                    <td>{row.manager_id || '-'}</td>
                    <td>{row.history_club}</td>
                    <td>{row.role || '-'}</td>
                    <td>{row.appointed_season || '-'}</td>
                    <td>{row.appointed_date || '-'}</td>
                    <td>{row.until_season || '-'}</td>
                    <td>{row.until_date || '-'}</td>
                    <td>{row.period_from || '-'}</td>
                    <td>{row.period_until || '-'}</td>
                    <td>{row.days_in_charge || '-'}</td>
                    <td>{row.matches || '-'}</td>
                    <td>{row.wins || '-'}</td>
                    <td>{row.draws || '-'}</td>
                    <td>{row.losses || '-'}</td>
                    <td>{row.players_used || '-'}</td>
                    <td>{row.avg_goals_for || '-'}</td>
                    <td>{row.avg_goals_against || '-'}</td>
                    <td>{row.points_per_match || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showAnimation && (
        <div className="logo-animation-overlay">
          <div className="logo-animation-container">
            <img src="/logo.png" alt="Logo" className="animated-logo" />
            <div className="animation-text">Starting Scraper...</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App

