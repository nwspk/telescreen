<?php
header('Content-Type: application/json');

$pages = glob(__DIR__ . '/../pages/*.html');

$pages = array_map(function($path) {
    return basename($path);
}, $pages);
echo json_encode($pages);
?>