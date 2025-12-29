<?php
// api/script.php
require_once 'db.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// 默认获取 ID=1 的剧本（后续可改为通过 GET 参数 ?id=1 获取）
$story_id = isset($_GET['id']) ? intval($_GET['id']) : 1;

// 1. 获取剧本元数据
$sql_story = "SELECT * FROM script_stories WHERE id = $story_id LIMIT 1";
$res_story = $conn->query($sql_story);
$story = $res_story->fetch_assoc();

if (!$story) {
    http_response_code(404);
    echo json_encode(['error' => 'Script not found']);
    exit;
}

// 2. 获取台词列表
$sql_lines = "SELECT * FROM script_lines WHERE story_id = $story_id ORDER BY sort_order ASC";
$res_lines = $conn->query($sql_lines);

$lines = [];
while ($row = $res_lines->fetch_assoc()) {
    $lines[] = [
        'id' => $row['id'], // 数据库ID
        'role' => $row['role_key'],
        'content' => $row['content'],
        'duration' => intval($row['duration_ms'])
    ];
}

// 3. 组装最终 JSON
$output = [
    'meta' => [
        'title' => $story['title'],
        'description' => $story['description'],
        'roleMap' => json_decode($story['role_map_json'], true)
    ],
    'lines' => $lines
];

echo json_encode($output);
