<?php
declare(strict_types=1);
header('Content-Type: application/json');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
$host = $_SERVER['HTTP_HOST'] ?? '';
$port = getenv('DASHBOARD_EXTERNAL_PORT') ?: '3000';
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if (!in_array($host, ["127.0.0.1:$port", "localhost:$port"], true)
    || ($origin !== '' && $origin !== "http://$host")) {
    http_response_code(403);
    echo json_encode(['error' => 'Local dashboard origin required']);
    exit;
}
$path = $_GET['path'] ?? '';
$method = $_SERVER['REQUEST_METHOD'];
$getPaths = ['session', 'status', 'logs/ac-worldserver', 'logs/ac-authserver', 'logs/ac-database', 'logs/ollama'];
if (!(($method === 'GET' && in_array($path, $getPaths, true)) || ($method === 'POST' && $path === 'action'))) {
    http_response_code(404);
    echo json_encode(['error' => 'Unknown control endpoint']);
    exit;
}
$body = file_get_contents('php://input', false, null, 0, 8193);
if (strlen($body) > 8192) {
    http_response_code(413);
    echo json_encode(['error' => 'Request too large']);
    exit;
}
$token = $_SERVER['HTTP_X_CONTROL_TOKEN'] ?? '';
if ($token !== '' && !preg_match('/^[A-Za-z0-9_-]{43}$/D', $token)) {
    http_response_code(403);
    echo json_encode(['error' => 'Invalid control token']);
    exit;
}
$context = stream_context_create(['http' => [
    'method' => $method, 'header' => "Content-Type: application/json\r\nX-Control-Token: $token\r\n",
    'content' => $method === 'POST' ? $body : '', 'timeout' => 12, 'ignore_errors' => true,
]]);
$result = @file_get_contents("http://host.docker.internal:8765/api/$path", false, $context);
if ($result === false) {
    http_response_code(503);
    echo json_encode(['error' => 'Control service unavailable. Run scripts/start-control.ps1 on Windows.']);
    exit;
}
preg_match('/\s(\d{3})\s/', $http_response_header[0], $match);
http_response_code((int)($match[1] ?? 502));
echo $result;
