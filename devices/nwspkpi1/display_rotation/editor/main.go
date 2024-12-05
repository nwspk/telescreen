package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

var pagesDir string
var configFile string

type PageConfig struct {
	Pages map[string]PageStatus `json:"pages"`
}

type PageStatus struct {
	Active bool `json:"active"`
	Order  int  `json:"order"`
}

func main() {
	var err error
	pagesDir = filepath.Join("..", "pages")
	pagesDir, err = filepath.Abs(pagesDir)
	if err != nil {
		log.Fatal("Could not resolve pages directory path:", err)
	}

	configFile = filepath.Join("..", "config", "pages-config.json")

	log.Printf("Starting editor server on :8081 (serving files from %s)", pagesDir)

	http.HandleFunc("/api/files", handleFiles)
	http.HandleFunc("/api/save", handleSave)
	http.HandleFunc("/api/config", handleConfig)
	http.HandleFunc("/api/toggle-status", handleToggleStatus)
	http.HandleFunc("/api/delete", handleDelete)

	fs := http.FileServer(http.Dir(pagesDir))
	http.Handle("/pages/", http.StripPrefix("/pages/", noCacheHandler(fs)))

	http.HandleFunc("/", serveEditor)

	log.Fatal(http.ListenAndServe(":8081", nil))
}

func handleConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	config, err := loadConfig()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(config)
}

func handleToggleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var request struct {
		Filename string     `json:"filename"`
		Config   PageConfig `json:"config"`
	}

	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if err := saveConfig(request.Config); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func loadConfig() (PageConfig, error) {
	var config PageConfig

	data, err := os.ReadFile(configFile)
	if err != nil {
		if os.IsNotExist(err) {
			return PageConfig{
				Pages: make(map[string]PageStatus),
			}, nil
		}
		return config, err
	}

	err = json.Unmarshal(data, &config)
	if config.Pages == nil {
		config.Pages = make(map[string]PageStatus)
	}
	return config, err
}

func saveConfig(config PageConfig) error {
	data, err := json.MarshalIndent(config, "", "    ")
	if err != nil {
		return err
	}
	return os.WriteFile(configFile, data, 0644)
}

func noCacheHandler(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
		w.Header().Set("Pragma", "no-cache")
		w.Header().Set("Expires", "0")
		h.ServeHTTP(w, r)
	})
}

func handleFiles(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
	w.Header().Set("Pragma", "no-cache")
	w.Header().Set("Expires", "0")

	files, err := filepath.Glob(filepath.Join(pagesDir, "*.html"))
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	var filteredFiles []string
	for _, f := range files {
		basename := filepath.Base(f)
		if basename != "rotator.html" {
			filteredFiles = append(filteredFiles, basename)
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(filteredFiles)
}

func handleSave(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	err := r.ParseMultipartForm(1 << 20)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	filename := r.FormValue("filename")
	content := r.FormValue("content")

	if !strings.HasSuffix(filename, ".html") || strings.Contains(filename, "/") {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	if filename == "rotator.html" {
		http.Error(w, "Cannot modify rotator.html", http.StatusForbidden)
		return
	}

	err = os.WriteFile(filepath.Join(pagesDir, filename), []byte(content), 0644)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func serveEditor(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}

	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(editorHTML))
}

func handleDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var request struct {
		Filename string `json:"filename"`
	}
	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Create rubbish directory if it doesn't exist
	rubbishDir := filepath.Join(pagesDir, "rubbish")
	if err := os.MkdirAll(rubbishDir, 0755); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Move file with timestamp to prevent conflicts
	timestamp := time.Now().Format("2006-01-02_15-04-05")
	oldPath := filepath.Join(pagesDir, request.Filename)
	newPath := filepath.Join(rubbishDir, request.Filename+"_"+timestamp)

	if err := os.Rename(oldPath, newPath); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Remove from config
	config, _ := loadConfig()
	delete(config.Pages, request.Filename)
	saveConfig(config)

	w.WriteHeader(http.StatusOK)
}
