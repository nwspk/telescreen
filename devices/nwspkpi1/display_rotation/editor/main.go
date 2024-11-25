package main

import (
    "encoding/json"
    "log"
    "net/http"
    "os"
    "path/filepath"
    "strings"
)

var pagesDir string

func main() {
    var err error
    pagesDir = filepath.Join("..", "pages")
    pagesDir, err = filepath.Abs(pagesDir)
    if err != nil {
        log.Fatal("Could not resolve pages directory path:", err)
    }
    
    log.Printf("Starting editor server on :8081 (serving files from %s)", pagesDir)
    
    http.HandleFunc("/api/files", handleFiles)
    http.HandleFunc("/api/save", handleSave)
    
    // Add no-cache handler for static files
    fs := http.FileServer(http.Dir(pagesDir))
    http.Handle("/pages/", http.StripPrefix("/pages/", noCacheHandler(fs)))
    
    http.HandleFunc("/", serveEditor)
    
    log.Fatal(http.ListenAndServe(":8081", nil))
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
    
    // Add cache control headers
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
