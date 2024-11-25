<?php
// Enable error reporting for debugging
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Configuration
$BASE_DIR = dirname(__DIR__); // Parent of config directory
$PAGES_DIR = $BASE_DIR . '/pages';
$CONFIG_DIR = $BASE_DIR . '/config';

// Debug logging function
function debug_log($message) {
    error_log("[" . date("Y-m-d H:i:s") . "] " . $message);
}

// Custom MIME type function
function get_mime_type($file_path) {
    $ext = strtolower(pathinfo($file_path, PATHINFO_EXTENSION));
    $mime_types = [
        'html' => 'text/html',
        'htm' => 'text/html',
        'php' => 'text/html',
        'css' => 'text/css',
        'js' => 'application/javascript',
        'json' => 'application/json',
        'png' => 'image/png',
        'jpg' => 'image/jpeg',
        'jpeg' => 'image/jpeg',
        'gif' => 'image/gif',
        'svg' => 'image/svg+xml',
    ];
    
    return isset($mime_types[$ext]) ? $mime_types[$ext] : 'text/plain';
}

debug_log("Router initialized");
debug_log("Base directory: " . $BASE_DIR);
debug_log("Pages directory: " . $PAGES_DIR);
debug_log("Config directory: " . $CONFIG_DIR);

// Get the requested URI
$request_uri = $_SERVER['REQUEST_URI'];
$parsed_path = parse_url($request_uri, PHP_URL_PATH);
debug_log("Router called with URI: " . $request_uri);
debug_log("Parsed URI path: " . $parsed_path);

// Remove leading slash and sanitize
$clean_path = ltrim($parsed_path, '/');
$clean_path = filter_var($clean_path, FILTER_SANITIZE_URL);

// Define which files can be served from config directory
$allowed_config_files = ['list-pages.php'];

// Determine which directory to serve from based on the request
if (in_array($clean_path, $allowed_config_files)) {
    $file_path = $CONFIG_DIR . '/' . $clean_path;
    debug_log("Serving config file: " . $file_path);
} else {
    $file_path = $PAGES_DIR . '/' . $clean_path;
    debug_log("Serving page file: " . $file_path);
}

// Check if file exists and serve it
if (file_exists($file_path)) {
    debug_log("File found: " . $file_path);
    
    // Handle PHP files
    if (pathinfo($file_path, PATHINFO_EXTENSION) === 'php') {
        debug_log("Executing PHP file: " . $file_path);
        require $file_path;
        exit;
    }
    
    // Handle static files
    $mime_type = get_mime_type($file_path);
    header("Content-Type: " . $mime_type);
    debug_log("Serving file with mime type: " . $mime_type);
    readfile($file_path);
    exit;
}

// If we get here, file wasn't found
debug_log("404 - No route found for: " . $clean_path);
header("HTTP/1.0 404 Not Found");
echo "404 - File not found: " . htmlspecialchars($clean_path);
