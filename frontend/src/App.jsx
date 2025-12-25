import React, { useState, useEffect } from 'react'
import axios from 'axios'
import * as XLSX from 'xlsx'
import Select from 'react-select'
import './index.css'

function App() {
  const [activeTab, setActiveTab] = useState('coaches') // 'coaches' or 'players'
  
  // Coach state
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
  
  // Player state
  const [playerStatus, setPlayerStatus] = useState({
    running: false,
    progress: {
      current: 0,
      total: 0,
      current_club: '',
      status: 'idle'
    }
  })
  const [playerResults, setPlayerResults] = useState([])
  
  // Shared state
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
  
  // Entity type and ID for URL-based scraping
  const [coachEntityType, setCoachEntityType] = useState('') // 'manager' or 'league'
  const [coachEntityId, setCoachEntityId] = useState('')
  const [playerEntityType, setPlayerEntityType] = useState('') // 'league' or 'club'
  const [playerEntityId, setPlayerEntityId] = useState('')

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
        setError(null)
        try {
          const allClubs = []
          const clubPromises = selectedLeagues.map(async (leagueId) => {
            const league = leagues.find(l => l.id === leagueId || l.url === leagueId)
            if (league) {
              console.log('Fetching clubs for league:', league.name, league.url)
              const response = await axios.post(`${API_BASE}/clubs`, {
                league_url: league.url
              })
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

  // Poll for coach status updates
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE}/status`)
        setStatus(response.data)
        
        if (response.data.results && response.data.results.length > 0) {
          setResults(response.data.results)
        }
      } catch (err) {
        console.error('Error fetching status:', err)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Poll for player status updates
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE}/player-status`)
        setPlayerStatus(response.data)
        
        if (response.data.results && response.data.results.length > 0) {
          setPlayerResults(response.data.results)
        }
      } catch (err) {
        console.error('Error fetching player status:', err)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  const startScraper = async () => {
    setLoading(true)
    setError(null)
    setResults([])
    setShowAnimation(true)
    
    setTimeout(() => {
      setShowAnimation(false)
    }, 3000)
    
    try {
      if (activeTab === 'coaches') {
        // Coach scraper logic
        // Check for URL-based scraping first
        if (coachEntityType && coachEntityId && coachEntityId.trim() !== '') {
          if (coachEntityType === 'manager') {
            // Extract manager ID from URL if it's a URL, otherwise treat as ID
            const managerId = coachEntityId.trim()
            const idMatch = managerId.match(/\/profil\/trainer\/(\d+)/)
            const extractedId = idMatch ? idMatch[1] : managerId
            await axios.post(`${API_BASE}/start-manager`, {
              manager_id: extractedId
            })
            return
          } else if (coachEntityType === 'league') {
            await axios.post(`${API_BASE}/start`, {
              league_url: coachEntityId.trim()
            })
            return
          }
        }
        
        
        if (selectedClubs.length > 0) {
          if (selectedClubs.length === 1) {
            const club = selectedClubs[0]
            await axios.post(`${API_BASE}/start-club`, {
              club_url: club.url,
              club_name: club.name
            })
          } else {
            await axios.post(`${API_BASE}/start-clubs`, {
              clubs: selectedClubs.map(club => ({
                url: club.url,
                name: club.name
              }))
            })
          }
        } else if (selectedLeagues.length > 0) {
          const selectedLeagueObjects = selectedLeagues.map(leagueId => 
            leagues.find(l => l.id === leagueId || l.url === leagueId)
          ).filter(Boolean)
          
          if (selectedLeagueObjects.length > 0) {
            if (selectedLeagueObjects.length === 1) {
              const league = selectedLeagueObjects[0]
              await axios.post(`${API_BASE}/start`, {
                league_url: league.url,
                league_name: league.name
              })
            } else {
              await axios.post(`${API_BASE}/start`, {
                league_urls: selectedLeagueObjects.map(l => ({ url: l.url, name: l.name }))
              })
            }
          }
        } else if (selectedContinent) {
          await axios.post(`${API_BASE}/start`, {
            continent: selectedContinent
          })
        } else {
          await axios.post(`${API_BASE}/start`)
        }
      } else {
        // Player scraper logic
        // Check for URL-based scraping first
        if (playerEntityType && playerEntityId && playerEntityId.trim() !== '') {
          if (playerEntityType === 'league') {
            await axios.post(`${API_BASE}/player-start`, {
              league_url: playerEntityId.trim()
            })
            return
          } else if (playerEntityType === 'club') {
            await axios.post(`${API_BASE}/player-start-club`, {
              club_url: playerEntityId.trim(),
              club_name: 'Club from URL' // Will be extracted from URL if needed
            })
            return
          }
        }
        
        if (selectedClubs.length > 0) {
          if (selectedClubs.length === 1) {
            const club = selectedClubs[0]
            await axios.post(`${API_BASE}/player-start-club`, {
              club_url: club.url,
              club_name: club.name
            })
          } else {
            await axios.post(`${API_BASE}/player-start-clubs`, {
              clubs: selectedClubs.map(club => ({
                url: club.url,
                name: club.name
              }))
            })
          }
        } else if (selectedLeagues.length > 0) {
          const selectedLeagueObjects = selectedLeagues.map(leagueId => 
            leagues.find(l => l.id === leagueId || l.url === leagueId)
          ).filter(Boolean)
          
          if (selectedLeagueObjects.length > 0) {
            if (selectedLeagueObjects.length === 1) {
              const league = selectedLeagueObjects[0]
              await axios.post(`${API_BASE}/player-start`, {
                league_url: league.url,
                league_name: league.name
              })
            } else {
              await axios.post(`${API_BASE}/player-start`, {
                league_urls: selectedLeagueObjects.map(l => ({ url: l.url, name: l.name }))
              })
            }
          }
        } else if (selectedContinent) {
          await axios.post(`${API_BASE}/player-start`, {
            continent: selectedContinent
          })
        } else {
          await axios.post(`${API_BASE}/player-start`)
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start scraper')
      setLoading(false)
      setShowAnimation(false)
    }
  }

  const stopScraper = async () => {
    try {
      if (activeTab === 'coaches') {
        await axios.post(`${API_BASE}/stop`)
      } else {
        await axios.post(`${API_BASE}/player-stop`)
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to stop scraper')
    }
  }

  const resetScraper = async () => {
    try {
      if (activeTab === 'coaches') {
        await axios.post(`${API_BASE}/reset`)
        setResults([])
        setStatus({
          running: false,
          progress: {
            current: 0,
            total: 0,
            current_club: '',
            status: 'idle'
          }
        })
      } else {
        await axios.post(`${API_BASE}/player-reset`)
        setPlayerResults([])
        setPlayerStatus({
          running: false,
          progress: {
            current: 0,
            total: 0,
            current_club: '',
            status: 'idle'
          }
        })
      }
      
      setError(null)
      setLoading(false)
      setShowAnimation(false)
      setSelectedContinent('')
      setSelectedLeagues([])
      setSelectedClubs([])
      setCoachEntityType('')
      setCoachEntityId('')
      setPlayerEntityType('')
      setPlayerEntityId('')
      setLeagues([])
      setClubs([])
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to reset scraper')
    }
  }

  const exportToExcel = () => {
    const dataToExport = activeTab === 'coaches' ? results : playerResults
    
    if (dataToExport.length === 0) {
      alert('No results to export')
      return
    }

    if (activeTab === 'coaches') {
      // Coach export logic
      const resultsByLeague = {}
      dataToExport.forEach(row => {
        const leagueName = row.league || 'Unknown League'
        if (!resultsByLeague[leagueName]) {
          resultsByLeague[leagueName] = []
        }
        resultsByLeague[leagueName].push(row)
      })

      const workbook = XLSX.utils.book_new()

      Object.keys(resultsByLeague).forEach(leagueName => {
        const leagueResults = resultsByLeague[leagueName]
        
        const headers = [
          'Current Club', 
          'Manager', 'Manager ID', 'Date of Birth', 'Preferred Formation',
          'History Club', 'Role', 
          'Appointed Date', 'Until Date',
          'Days in Charge',
          'Matches', 'Wins', 'Draws', 'Losses', 'Players Used',
          'Avg Goals For', 'Avg Goals Against', 'Points Per Match'
        ]
        
        const data = [
          headers,
          ...leagueResults.map(row => [
            row.current_club || '',
            row.manager || '',
            row.manager_id || '',
            row.date_of_birth || '',
            row.preferred_formation || '',
            row.history_club || '',
            row.role || '',
            row.appointed_date || '',
            row.until_date || '',
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
        
        const worksheet = XLSX.utils.aoa_to_sheet(data)
        
        let sheetName = leagueName
          .replace(/[\\\/\?\*\[\]:]/g, '_')
          .substring(0, 31)
        
        if (!sheetName) {
          sheetName = 'Sheet'
        }
        
        XLSX.utils.book_append_sheet(workbook, worksheet, sheetName)
      })

      const fileName = `coach_achievements_${new Date().toISOString().split('T')[0]}.xlsx`
      XLSX.writeFile(workbook, fileName)
    } else {
      // Player export logic
      const resultsByLeague = {}
      dataToExport.forEach(row => {
        const leagueName = row.league || 'Unknown League'
        if (!resultsByLeague[leagueName]) {
          resultsByLeague[leagueName] = []
        }
        resultsByLeague[leagueName].push(row)
      })

      const workbook = XLSX.utils.book_new()

      Object.keys(resultsByLeague).forEach(leagueName => {
        const leagueResults = resultsByLeague[leagueName]
        
        const headers = [
          'Current Club',
          'Player Name', 'Player ID', 'Jersey Number', 'Nationality',
          'Date of Birth', 'Caps', 'Goals', 'Position',
          'Height', 'Foot', 'Current Market Value'
        ]
        
        const data = [
          headers,
          ...leagueResults.map(row => [
            row.current_club || '',
            row.player_name || '',
            row.player_id || '',
            row.jersey_number || '',
            row.nationality || '',
            row.date_of_birth || '',
            row.caps || '',
            row.goals || '',
            row.position || '',
            row.height || '',
            row.foot || '',
            row.current_market_value || ''
          ])
        ]
        
        const worksheet = XLSX.utils.aoa_to_sheet(data)
        
        let sheetName = leagueName
          .replace(/[\\\/\?\*\[\]:]/g, '_')
          .substring(0, 31)
        
        if (!sheetName) {
          sheetName = 'Sheet'
        }
        
        XLSX.utils.book_append_sheet(workbook, worksheet, sheetName)
      })

      const fileName = `player_data_${new Date().toISOString().split('T')[0]}.xlsx`
      XLSX.writeFile(workbook, fileName)
    }
  }

  const currentStatus = activeTab === 'coaches' ? status : playerStatus
  const currentResults = activeTab === 'coaches' ? results : playerResults
  const progressPercentage = currentStatus.progress.total > 0 
    ? Math.round((currentStatus.progress.current / currentStatus.progress.total) * 100) 
    : 0

  return (
    <div className="container">
      <div className="header">
        <div className="logo-container">
          <img src="/logo.png" alt="Logo" className={`logo ${currentStatus.running ? 'logo-running' : ''}`} />
          <p>
            {currentStatus.running ? (
              <span className="running-message">
                <strong>NNNUUU...</strong> Another operation is currently running. Please wait for it to complete.
              </span>
            ) : (
              <>
                <strong>NNNUUUU...</strong> Extract {activeTab === 'coaches' ? 'coach career history' : 'player data'} from top football clubs
              </>
            )}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ 
        display: 'flex', 
        gap: '10px', 
        marginBottom: '20px',
        borderBottom: '2px solid #334155',
        paddingBottom: '10px'
      }}>
        <button
          onClick={() => setActiveTab('coaches')}
          style={{
            padding: '10px 20px',
            backgroundColor: activeTab === 'coaches' ? '#3b82f6' : '#1e293b',
            color: '#e2e8f0',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: activeTab === 'coaches' ? 'bold' : 'normal'
          }}
        >
          Coaches
        </button>
        <button
          onClick={() => setActiveTab('players')}
          style={{
            padding: '10px 20px',
            backgroundColor: activeTab === 'players' ? '#3b82f6' : '#1e293b',
            color: '#e2e8f0',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: activeTab === 'players' ? 'bold' : 'normal'
          }}
        >
          Players
        </button>
      </div>

      <div className="controls">
        <div className="selection-section">
          {/* ID-based scraping section */}
          {activeTab === 'coaches' && (
            <>
              <div className="select-group">
                <label htmlFor="coach-entity-type">Scrape by URL (optional):</label>
                <Select
                  id="coach-entity-type"
                  value={coachEntityType ? { value: coachEntityType, label: coachEntityType === 'manager' ? 'Manager' : 'League' } : null}
                  onChange={(option) => {
                    setCoachEntityType(option ? option.value : '')
                    setCoachEntityId('') // Clear ID when changing type
                  }}
                  options={[
                    { value: 'manager', label: 'Manager' },
                    { value: 'league', label: 'League' }
                  ]}
                  isDisabled={currentStatus.running}
                  placeholder="-- Select Entity Type --"
                  isClearable
                  className="react-select-container"
                  classNamePrefix="react-select"
                />
              </div>
              {coachEntityType && (
                <div className="select-group">
                  <label htmlFor="coach-entity-id">
                    {coachEntityType === 'manager' ? 'Manager URL' : 'League URL'}:
                  </label>
                  <input
                    id="coach-entity-id"
                    type="text"
                    value={coachEntityId}
                    onChange={(e) => {
                      // Allow full URL input
                      setCoachEntityId(e.target.value)
                    }}
                    placeholder={coachEntityType === 'manager' 
                      ? 'Enter Manager URL (e.g., https://www.transfermarkt.com/.../profil/trainer/12345)' 
                      : 'Enter League URL (e.g., https://www.transfermarkt.com/.../startseite/wettbewerb/GB1)'}
                    disabled={currentStatus.running}
                    style={{
                      padding: '8px 12px',
                      fontSize: '1rem',
                      border: '1px solid #475569',
                      borderRadius: '4px',
                      backgroundColor: '#1e293b',
                      color: '#e2e8f0',
                      width: '100%',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              )}
            </>
          )}
          
          {activeTab === 'players' && (
            <>
              <div className="select-group">
                <label htmlFor="player-entity-type">Scrape by URL (optional):</label>
                <Select
                  id="player-entity-type"
                  value={playerEntityType ? { value: playerEntityType, label: playerEntityType === 'league' ? 'League' : 'Club' } : null}
                  onChange={(option) => {
                    setPlayerEntityType(option ? option.value : '')
                    setPlayerEntityId('') // Clear ID when changing type
                  }}
                  options={[
                    { value: 'league', label: 'League' },
                    { value: 'club', label: 'Club' }
                  ]}
                  isDisabled={currentStatus.running}
                  placeholder="-- Select Entity Type --"
                  isClearable
                  className="react-select-container"
                  classNamePrefix="react-select"
                />
              </div>
              {playerEntityType && (
                <div className="select-group">
                  <label htmlFor="player-entity-id">
                    {playerEntityType === 'league' ? 'League URL' : 'Club URL'}:
                  </label>
                  <input
                    id="player-entity-id"
                    type="text"
                    value={playerEntityId}
                    onChange={(e) => {
                      // Allow full URL input
                      setPlayerEntityId(e.target.value)
                    }}
                    placeholder={playerEntityType === 'league'
                      ? 'Enter League URL (e.g., https://www.transfermarkt.com/.../startseite/wettbewerb/GB1)'
                      : 'Enter Club URL (e.g., https://www.transfermarkt.com/.../startseite/verein/418)'}
                    disabled={currentStatus.running}
                    style={{
                      padding: '8px 12px',
                      fontSize: '1rem',
                      border: '1px solid #475569',
                      borderRadius: '4px',
                      backgroundColor: '#1e293b',
                      color: '#e2e8f0',
                      width: '100%',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              )}
            </>
          )}

          <div className="select-group">
            <label htmlFor="continent-select">Select Continent:</label>
            <Select
              id="continent-select"
              value={continents.find(c => c.value === selectedContinent) || null}
              onChange={(option) => setSelectedContinent(option ? option.value : '')}
              options={continents}
                isDisabled={currentStatus.running || (activeTab === 'coaches' && coachEntityId !== '') || (activeTab === 'players' && playerEntityId !== '')}
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
                isDisabled={currentStatus.running || loadingLeagues || (activeTab === 'coaches' && coachEntityId !== '') || (activeTab === 'players' && playerEntityId !== '')}
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
                isDisabled={currentStatus.running || loadingClubs || (activeTab === 'coaches' && coachEntityId !== '') || (activeTab === 'players' && playerEntityId !== '')}
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
            disabled={currentStatus.running || loading || (activeTab === 'coaches' && coachEntityId === '' && selectedClubs.length === 0 && selectedLeagues.length === 0 && !selectedContinent) || (activeTab === 'players' && playerEntityId === '' && selectedClubs.length === 0 && selectedLeagues.length === 0 && !selectedContinent)}
          >
            ▶ Start Scraper
          </button>
          <button 
            className="btn btn-danger" 
            onClick={stopScraper} 
            disabled={!currentStatus.running}
          >
            ⏹ Stop Scraper
          </button>
          <button 
            className="btn btn-secondary" 
            onClick={resetScraper} 
            disabled={currentStatus.running}
          >
            🔄 Reset
          </button>
          {currentResults.length > 0 && (
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
          <strong>Status:</strong> {currentStatus.progress.status || 'idle'}
        </div>
        {currentStatus.progress.current_club && (
          <div className="status-text">
            <strong>Current Club:</strong> {currentStatus.progress.current_club}
          </div>
        )}
        {currentStatus.progress.total > 0 && (
          <>
            <div className="status-text">
              <strong>Progress:</strong> {currentStatus.progress.current} / {currentStatus.progress.total} clubs
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
          {currentResults.length > 0 && (
            <span style={{ color: '#94a3b8', fontSize: '1rem' }}>
              {currentResults.length} {activeTab === 'coaches' ? 'career entr' + (currentResults.length !== 1 ? 'ies' : 'y') : 'player' + (currentResults.length !== 1 ? 's' : '')} found
            </span>
          )}
        </div>

        {currentStatus.running && currentResults.length === 0 && (
          <div className="loading">
            <p>⏳ Scraping in progress... Please wait...</p>
          </div>
        )}

        {!currentStatus.running && currentResults.length === 0 && currentStatus.progress.status === 'idle' && (
          <div className="empty-state">
            <h3>No results yet</h3>
            <p>Click "Start Scraper" to begin extracting {activeTab === 'coaches' ? 'coach career history' : 'player data'}</p>
          </div>
        )}

        {currentResults.length > 0 && (
          <div className="table-container">
            <table>
              <thead>
                {activeTab === 'coaches' ? (
                  <tr>
                    <th>Current Club</th>
                    <th>Manager</th>
                    <th>Manager ID</th>
                    <th>Date of Birth</th>
                    <th>Preferred Formation</th>
                    <th>History Club</th>
                    <th>Role</th>
                    <th>Appointed Date</th>
                    <th>Until Date</th>
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
                ) : (
                  <tr>
                    <th>Current Club</th>
                    <th>Player Name</th>
                    <th>Player ID</th>
                    <th>Jersey Number</th>
                    <th>Nationality</th>
                    <th>Date of Birth</th>
                    <th>Caps</th>
                    <th>Goals</th>
                    <th>Position</th>
                    <th>Height</th>
                    <th>Foot</th>
                    <th>Current Market Value</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {activeTab === 'coaches' ? (
                  currentResults.map((row, index) => (
                    <tr key={index}>
                      <td>{row.current_club}</td>
                      <td>{row.manager}</td>
                      <td>{row.manager_id || '-'}</td>
                      <td>{row.date_of_birth || '-'}</td>
                      <td>{row.preferred_formation || '-'}</td>
                      <td>{row.history_club}</td>
                      <td>{row.role || '-'}</td>
                      <td>{row.appointed_date || '-'}</td>
                      <td>{row.until_date || '-'}</td>
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
                  ))
                ) : (
                  currentResults.map((row, index) => (
                    <tr key={index}>
                      <td>{row.current_club}</td>
                      <td>{row.player_name}</td>
                      <td>{row.player_id || '-'}</td>
                      <td>{row.jersey_number || '-'}</td>
                      <td>{row.nationality || '-'}</td>
                      <td>{row.date_of_birth || '-'}</td>
                      <td>{row.caps || '-'}</td>
                      <td>{row.goals || '-'}</td>
                      <td>{row.position || '-'}</td>
                      <td>{row.height || '-'}</td>
                      <td>{row.foot || '-'}</td>
                      <td>{row.current_market_value || '-'}</td>
                    </tr>
                  ))
                )}
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
