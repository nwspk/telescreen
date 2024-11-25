<?php
header('Content-Type: application/json');
error_reporting(E_ALL);
ini_set('display_errors', 1);

error_log("list-pages.php started");

// Get the directory of this script (config directory)
$config_dir = __DIR__;
error_log("Config directory: " . $config_dir);

// Get the pages directory (one level up then into pages)
$pages_dir = realpath($config_dir . '/../pages');
error_log("Pages directory: " . $pages_dir);

// Look for HTML files in the pages directory
$pages = glob($pages_dir . '/*.html');
error_log("Found files: " . print_r($pages, true));

// Convert to basenames
$pages = array_map('basename', $pages);

// Filter out rotator.html
$pages = array_filter($pages, function($page) {
    return $page !== 'rotator.html';
});

// Get configuration
$config_file = $config_dir . '/pages-config.json';
error_log("Looking for config at: " . $config_file);

$final_pages = [];

if (file_exists($config_file)) {
    $config = json_decode(file_get_contents($config_file), true);
    error_log("Config loaded: " . print_r($config, true));
    
    foreach ($pages as $page) {
        if (isset($config['pages'][$page]) && $config['pages'][$page]['active']) {
            $final_pages[] = [
                'filename' => $page,
                'order' => $config['pages'][$page]['order']
            ];
        }
    }
    
    // Sort pages by order
    usort($final_pages, function($a, $b) {
        return $a['order'] - $b['order'];
    });
    
    // Extract just the filenames in the correct order
    $pages = array_map(function($page) {
        return $page['filename'];
    }, $final_pages);
} else {
    // If no config exists, keep all pages active
    $pages = array_values($pages);
}

error_log("Final page list: " . print_r($pages, true));
echo json_encode($pages);
?>
