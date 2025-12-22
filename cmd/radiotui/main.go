package main

import (
	"database/sql"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	_ "github.com/mattn/go-sqlite3"
)

// Styles
var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FF00FF")).
			Background(lipgloss.Color("#1a1a1a")).
			Padding(0, 2)

	headerStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#00FFFF")).
			BorderStyle(lipgloss.NormalBorder()).
			BorderBottom(true).
			BorderForeground(lipgloss.Color("#FF00FF"))

	selectedItemStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(lipgloss.Color("#FF00FF")).
				Background(lipgloss.Color("#2a2a2a"))

	normalItemStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#00FFFF"))

	statsStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#00FF00")).
			BorderStyle(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#FF00FF")).
			Padding(1, 2).
			MarginTop(1)

	detailStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FFFFFF")).
			BorderStyle(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#00FFFF")).
			Padding(1, 2).
			MarginTop(1)

	helpStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#666666")).
			MarginTop(1)
)

type view int

const (
	trackListView view = iota
	trackDetailView
	statsView
	playHistoryView
)

type sortColumn int

const (
	sortByArtist sortColumn = iota
	sortByTitle
	sortByAlbum
	sortByDuration
	sortByEnergy
	sortByPlays
)

type historySortColumn int

const (
	sortHistoryByTime historySortColumn = iota
	sortHistoryBySource
	sortHistoryByTrack
)

type model struct {
	db              *sql.DB
	view            view
	table           table.Model
	historyTable    table.Model
	viewport        viewport.Model
	tracks          []Track
	playHistory     []PlayEntry
	stats           Stats
	selected        int
	width           int
	height          int
	ready           bool
	sortCol         sortColumn
	sortAsc         bool
	historySortCol  historySortColumn
	historySortAsc  bool
}

type Track struct {
	ID           string
	Path         string
	Kind         string
	DurationSec  float64
	LoudnessLUFS float64
	TruePeakDBTP float64
	EnergyLevel  int
	Title        string
	Artist       string
	Album        string
	CreatedAt    string
	PlayCount    int
	LastPlayedAt string
}

type PlayEntry struct {
	ID        int
	AssetID   string
	PlayedAt  string
	Source    string
	TrackInfo string
}

type Stats struct {
	TotalTracks   int
	TotalPlays    int
	TotalDuration float64
	AvgEnergy     float64
	Tracks24h     int
	TopArtist     string
	TopTrack      string
}

func main() {
	// Check if database exists
	dbPath := "./db/radio.sqlite3"
	if len(os.Args) > 1 {
		dbPath = os.Args[1]
	}

	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error opening database: %v\n", err)
		os.Exit(1)
	}
	defer db.Close()

	m := initialModel(db)
	p := tea.NewProgram(m, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func initialModel(db *sql.DB) model {
	// Load initial data with default sort
	tracks := loadTracks(db, sortByArtist, true)
	stats := loadStats(db)

	// Create table
	columns := []table.Column{
		{Title: "Artist", Width: 20},
		{Title: "Title", Width: 25},
		{Title: "Album", Width: 20},
		{Title: "Duration", Width: 8},
		{Title: "Energy", Width: 6},
		{Title: "Plays", Width: 6},
		{Title: "Last Played", Width: 15},
	}

	rows := []table.Row{}
	for _, t := range tracks {
		rows = append(rows, table.Row{
			truncate(t.Artist, 20),
			truncate(t.Title, 25),
			truncate(t.Album, 20),
			formatDuration(t.DurationSec),
			fmt.Sprintf("%d", t.EnergyLevel),
			fmt.Sprintf("%d", t.PlayCount),
			formatRelativeTime(t.LastPlayedAt),
		})
	}

	t := table.New(
		table.WithColumns(columns),
		table.WithRows(rows),
		table.WithFocused(true),
		table.WithHeight(20),
	)

	s := table.DefaultStyles()
	s.Header = s.Header.
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color("#FF00FF")).
		BorderBottom(true).
		Bold(true).
		Foreground(lipgloss.Color("#00FFFF"))
	s.Selected = s.Selected.
		Foreground(lipgloss.Color("#FF00FF")).
		Background(lipgloss.Color("#2a2a2a")).
		Bold(true)
	t.SetStyles(s)

	// Create history table
	historyColumns := []table.Column{
		{Title: "Time", Width: 20},
		{Title: "Source", Width: 10},
		{Title: "Track", Width: 60},
	}

	ht := table.New(
		table.WithColumns(historyColumns),
		table.WithRows([]table.Row{}),
		table.WithFocused(false),
		table.WithHeight(20),
	)
	ht.SetStyles(s)

	return model{
		db:             db,
		view:           trackListView,
		table:          t,
		historyTable:   ht,
		tracks:         tracks,
		stats:          stats,
		selected:       0,
		sortCol:        sortByArtist,
		sortAsc:        true,
		historySortCol: sortHistoryByTime,
		historySortAsc: false, // Most recent first by default
	}
}

func (m model) Init() tea.Cmd {
	return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.ready = true
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			return m, tea.Quit

		case "1":
			m.view = trackListView
			return m, nil

		case "2":
			m.view = trackDetailView
			m.selected = m.table.Cursor()
			return m, nil

		case "3":
			m.view = statsView
			return m, nil

		case "4":
			m.view = playHistoryView
			m.playHistory = loadPlayHistory(m.db, 50, m.historySortCol, m.historySortAsc)
			m.updateHistoryTableRows()
			m.historyTable.Focus()
			return m, nil

		case "r":
			// Refresh data
			m.tracks = loadTracks(m.db, m.sortCol, m.sortAsc)
			m.stats = loadStats(m.db)
			m.updateTableRows()
			return m, nil

		case "tab":
			// Cycle through sort columns
			if m.view == trackListView {
				m.sortCol = (m.sortCol + 1) % 6
				m.tracks = loadTracks(m.db, m.sortCol, m.sortAsc)
				m.updateTableRows()
			} else if m.view == playHistoryView {
				m.historySortCol = (m.historySortCol + 1) % 3
				m.playHistory = loadPlayHistory(m.db, 50, m.historySortCol, m.historySortAsc)
				m.updateHistoryTableRows()
			}
			return m, nil

		case "shift+tab":
			// Reverse sort direction
			if m.view == trackListView {
				m.sortAsc = !m.sortAsc
				m.tracks = loadTracks(m.db, m.sortCol, m.sortAsc)
				m.updateTableRows()
			} else if m.view == playHistoryView {
				m.historySortAsc = !m.historySortAsc
				m.playHistory = loadPlayHistory(m.db, 50, m.historySortCol, m.historySortAsc)
				m.updateHistoryTableRows()
			}
			return m, nil
		}
	}

	// Update the appropriate component based on view
	switch m.view {
	case trackListView:
		m.table, cmd = m.table.Update(msg)
	case trackDetailView:
		m.viewport, cmd = m.viewport.Update(msg)
	case playHistoryView:
		m.historyTable, cmd = m.historyTable.Update(msg)
	}

	return m, cmd
}

func (m model) View() string {
	if !m.ready {
		return "Loading LAST BYTE RADIO Database..."
	}

	var content string

	// Title bar
	title := titleStyle.Render("🎵 LAST BYTE RADIO 🎵 Database Browser")

	switch m.view {
	case trackListView:
		content = m.renderTrackList()
	case trackDetailView:
		content = m.renderTrackDetail()
	case statsView:
		content = m.renderStats()
	case playHistoryView:
		content = m.renderPlayHistory()
	}

	help := helpStyle.Render("[1] Tracks [2] Detail [3] Stats [4] History [Tab] Sort Column [Shift+Tab] Reverse [r] Refresh [q] Quit")

	return lipgloss.JoinVertical(
		lipgloss.Left,
		title,
		"",
		content,
		"",
		help,
	)
}

func (m model) renderTrackList() string {
	sortIndicator := "↑"
	if !m.sortAsc {
		sortIndicator = "↓"
	}
	sortColName := []string{"Artist", "Title", "Album", "Duration", "Energy", "Plays"}[m.sortCol]
	header := headerStyle.Render(fmt.Sprintf("Track Library (%d tracks) - Sort: %s %s",
		len(m.tracks), sortColName, sortIndicator))
	return lipgloss.JoinVertical(lipgloss.Left, header, m.table.View())
}

func (m *model) updateTableRows() {
	rows := []table.Row{}
	for _, t := range m.tracks {
		rows = append(rows, table.Row{
			truncate(t.Artist, 20),
			truncate(t.Title, 25),
			truncate(t.Album, 20),
			formatDuration(t.DurationSec),
			fmt.Sprintf("%d", t.EnergyLevel),
			fmt.Sprintf("%d", t.PlayCount),
			formatRelativeTime(t.LastPlayedAt),
		})
	}
	m.table.SetRows(rows)
}

func (m model) renderTrackDetail() string {
	if m.selected >= len(m.tracks) {
		return "No track selected"
	}

	t := m.tracks[m.selected]

	details := fmt.Sprintf(`╔═══════════════════════════════════════════════════════════════╗
║  TRACK DETAILS                                                 ║
╚═══════════════════════════════════════════════════════════════╝

🎵  Title:      %s
👤  Artist:     %s
💿  Album:      %s
⏱️   Duration:   %s
🔊  Loudness:   %.1f LUFS
📊  True Peak:  %.1f dBTP
⚡  Energy:     %d/100
🎯  Kind:       %s
📈  Plays:      %d
📅  Added:      %s
🕐  Last Played: %s
🔑  ID:         %s
📁  Path:       %s
`,
		t.Title,
		t.Artist,
		t.Album,
		formatDuration(t.DurationSec),
		t.LoudnessLUFS,
		t.TruePeakDBTP,
		t.EnergyLevel,
		t.Kind,
		t.PlayCount,
		formatTimestamp(t.CreatedAt),
		formatRelativeTime(t.LastPlayedAt),
		t.ID[:12]+"...",
		t.Path,
	)

	return detailStyle.Render(details)
}

func (m model) renderStats() string {
	s := m.stats

	stats := fmt.Sprintf(`╔═══════════════════════════════════════════════════════════════╗
║  STATION STATISTICS                                            ║
╚═══════════════════════════════════════════════════════════════╝

📚  Total Tracks:       %d
🎵  Total Plays:        %d
⏱️   Total Duration:     %s
⚡  Average Energy:     %.1f/100
📈  Plays (24h):        %d

🏆  Top Artist:         %s
🥇  Most Played:        %s
`,
		s.TotalTracks,
		s.TotalPlays,
		formatDuration(s.TotalDuration),
		s.AvgEnergy,
		s.Tracks24h,
		s.TopArtist,
		s.TopTrack,
	)

	return statsStyle.Render(stats)
}

func (m model) renderPlayHistory() string {
	sortIndicator := "↑"
	if !m.historySortAsc {
		sortIndicator = "↓"
	}
	sortColName := []string{"Time", "Source", "Track"}[m.historySortCol]
	header := headerStyle.Render(fmt.Sprintf("Play History (%d plays) - Sort: %s %s",
		len(m.playHistory), sortColName, sortIndicator))
	return lipgloss.JoinVertical(lipgloss.Left, header, m.historyTable.View())
}

func (m *model) updateHistoryTableRows() {
	rows := []table.Row{}
	for _, p := range m.playHistory {
		rows = append(rows, table.Row{
			formatTimestamp(p.PlayedAt),
			p.Source,
			truncate(p.TrackInfo, 60),
		})
	}
	m.historyTable.SetRows(rows)
}

// Database queries

func loadTracks(db *sql.DB, sortCol sortColumn, ascending bool) []Track {
	orderBy := "a.artist, a.title"
	switch sortCol {
	case sortByArtist:
		orderBy = "a.artist"
	case sortByTitle:
		orderBy = "a.title"
	case sortByAlbum:
		orderBy = "a.album"
	case sortByDuration:
		orderBy = "a.duration_sec"
	case sortByEnergy:
		orderBy = "a.energy_level"
	case sortByPlays:
		orderBy = "play_count"
	}

	if !ascending {
		orderBy += " DESC"
	}

	query := fmt.Sprintf(`
		SELECT
			a.id, a.path, a.kind, a.duration_sec,
			COALESCE(a.loudness_lufs, 0), COALESCE(a.true_peak_dbtp, 0),
			COALESCE(a.energy_level, 0),
			COALESCE(a.title, 'Unknown'),
			COALESCE(a.artist, 'Unknown'),
			COALESCE(a.album, 'Unknown'),
			a.created_at,
			COUNT(p.id) as play_count,
			MAX(p.played_at) as last_played_at
		FROM assets a
		LEFT JOIN play_history p ON a.id = p.asset_id
		WHERE a.kind = 'music'
		GROUP BY a.id
		ORDER BY %s
	`, orderBy)

	rows, err := db.Query(query)
	if err != nil {
		return []Track{}
	}
	defer rows.Close()

	var tracks []Track
	for rows.Next() {
		var t Track
		var lastPlayed sql.NullString
		err := rows.Scan(
			&t.ID, &t.Path, &t.Kind, &t.DurationSec,
			&t.LoudnessLUFS, &t.TruePeakDBTP, &t.EnergyLevel,
			&t.Title, &t.Artist, &t.Album, &t.CreatedAt, &t.PlayCount,
			&lastPlayed,
		)
		if err != nil {
			continue
		}
		if lastPlayed.Valid {
			t.LastPlayedAt = lastPlayed.String
		}
		tracks = append(tracks, t)
	}

	return tracks
}

func loadStats(db *sql.DB) Stats {
	var s Stats

	// Total tracks
	db.QueryRow("SELECT COUNT(*) FROM assets WHERE kind = 'music'").Scan(&s.TotalTracks)

	// Total plays
	db.QueryRow("SELECT COUNT(*) FROM play_history WHERE source = 'music'").Scan(&s.TotalPlays)

	// Total duration
	db.QueryRow("SELECT COALESCE(SUM(duration_sec), 0) FROM assets WHERE kind = 'music'").Scan(&s.TotalDuration)

	// Average energy
	db.QueryRow("SELECT COALESCE(AVG(energy_level), 0) FROM assets WHERE kind = 'music' AND energy_level IS NOT NULL").Scan(&s.AvgEnergy)

	// Plays in last 24h
	db.QueryRow(`
		SELECT COUNT(*) FROM play_history
		WHERE source = 'music'
		AND datetime(played_at) > datetime('now', '-24 hours')
	`).Scan(&s.Tracks24h)

	// Top artist
	db.QueryRow(`
		SELECT COALESCE(a.artist, 'Unknown')
		FROM assets a
		JOIN play_history p ON a.id = p.asset_id
		WHERE p.source = 'music'
		GROUP BY a.artist
		ORDER BY COUNT(*) DESC
		LIMIT 1
	`).Scan(&s.TopArtist)

	// Most played track
	db.QueryRow(`
		SELECT COALESCE(a.title || ' - ' || a.artist, 'Unknown')
		FROM assets a
		JOIN play_history p ON a.id = p.asset_id
		WHERE p.source = 'music'
		GROUP BY a.id
		ORDER BY COUNT(*) DESC
		LIMIT 1
	`).Scan(&s.TopTrack)

	return s
}

func loadPlayHistory(db *sql.DB, limit int, sortCol historySortColumn, ascending bool) []PlayEntry {
	orderBy := "p.played_at DESC"
	switch sortCol {
	case sortHistoryByTime:
		orderBy = "p.played_at"
	case sortHistoryBySource:
		orderBy = "p.source"
	case sortHistoryByTrack:
		orderBy = "track_info"
	}

	if !ascending {
		if strings.HasSuffix(orderBy, " DESC") {
			orderBy = strings.TrimSuffix(orderBy, " DESC")
		} else {
			orderBy += " DESC"
		}
	}

	query := fmt.Sprintf(`
		SELECT
			p.id, p.asset_id, p.played_at, p.source,
			COALESCE(a.title || ' - ' || a.artist, p.asset_id) as track_info
		FROM play_history p
		LEFT JOIN assets a ON p.asset_id = a.id
		ORDER BY %s
		LIMIT ?
	`, orderBy)

	rows, err := db.Query(query, limit)
	if err != nil {
		return []PlayEntry{}
	}
	defer rows.Close()

	var entries []PlayEntry
	for rows.Next() {
		var e PlayEntry
		err := rows.Scan(&e.ID, &e.AssetID, &e.PlayedAt, &e.Source, &e.TrackInfo)
		if err != nil {
			continue
		}
		entries = append(entries, e)
	}

	return entries
}

// Utility functions

func formatDuration(sec float64) string {
	d := time.Duration(sec) * time.Second
	m := int(d.Minutes())
	s := int(d.Seconds()) % 60
	return fmt.Sprintf("%d:%02d", m, s)
}

func formatTimestamp(ts string) string {
	t, err := time.Parse(time.RFC3339, ts)
	if err != nil {
		return ts
	}
	return t.Local().Format("Jan 02 15:04:05")
}

func truncate(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max-3] + "..."
}

func formatRelativeTime(ts string) string {
	if ts == "" {
		return "never"
	}

	t, err := time.Parse(time.RFC3339, ts)
	if err != nil {
		return "unknown"
	}

	diff := time.Since(t)

	if diff < time.Minute {
		return "just now"
	} else if diff < time.Hour {
		mins := int(diff.Minutes())
		return fmt.Sprintf("%dm ago", mins)
	} else if diff < 24*time.Hour {
		hours := int(diff.Hours())
		return fmt.Sprintf("%dh ago", hours)
	} else if diff < 7*24*time.Hour {
		days := int(diff.Hours() / 24)
		return fmt.Sprintf("%dd ago", days)
	} else if diff < 30*24*time.Hour {
		weeks := int(diff.Hours() / 24 / 7)
		return fmt.Sprintf("%dw ago", weeks)
	} else if diff < 365*24*time.Hour {
		months := int(diff.Hours() / 24 / 30)
		return fmt.Sprintf("%dmo ago", months)
	} else {
		years := int(diff.Hours() / 24 / 365)
		return fmt.Sprintf("%dy ago", years)
	}
}
