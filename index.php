<?php
$webDir = __DIR__ . '/web';
$backendBaseUrl = 'http://127.0.0.1:5000';

$requestUri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '/';
$parsed = parse_url($requestUri);
$path = isset($parsed['path']) ? $parsed['path'] : '/';
$query = isset($parsed['query']) ? $parsed['query'] : '';
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$body = file_get_contents('php://input');

function proxyToBackend(string $backendBaseUrl, string $path, string $query, string $method, string $body): void {
    $backendUrl = $backendBaseUrl . $path;
    if ($query !== '') {
        $backendUrl .= '?' . $query;
    }

    $ch = curl_init($backendUrl);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 180);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Accept: application/json, text/plain, */*',
        'X-Forwarded-By: PHP-Proxy'
    ]);

    if ($body !== '') {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
    }

    $response = curl_exec($ch);
    $curlErrNo = curl_errno($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    curl_close($ch);

    if ($curlErrNo !== 0) {
        http_response_code(502);
        echo json_encode(['error' => 'Backend unavailable']);
        return;
    }

    $headers = substr($response, 0, $headerSize);
    $bodyResponse = substr($response, $headerSize);
    $lines = explode("\r\n", $headers);

    foreach ($lines as $line) {
        if (stripos($line, 'Content-Type:') === 0) {
            header(rtrim($line));
        } elseif (stripos($line, 'Location:') === 0) {
            header(rtrim($line));
        } elseif (stripos($line, 'Access-Control-Allow-') === 0) {
            header(rtrim($line));
        }
    }

    http_response_code($httpCode);
    echo $bodyResponse;
}

if ($path === '/' || $path === '/index.html') {
    header('Content-Type: text/html; charset=utf-8');
    readfile($webDir . '/index.html');
    exit;
}

if (in_array($path, ['/app.js', '/styles.css', '/api-config.js'], true)) {
    $type = $path === '/app.js' ? 'application/javascript' : ($path === '/styles.css' ? 'text/css' : 'application/javascript');
    header('Content-Type: ' . $type);
    readfile($webDir . $path);
    exit;
}

proxyToBackend($backendBaseUrl, $path, $query, $method, $body);
