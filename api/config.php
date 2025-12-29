<?php
// api/config.php
require_once 'db.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

// 初始化默认结构
$config = [
    'asr' => [],
    'tts' => [],
    'llm' => []
];

// 从数据库查询配置
$sql = "SELECT category, key_name, value FROM script_configs";
$result = $conn->query($sql);

if ($result) {
    while ($row = $result->fetch_assoc()) {
        $cat = $row['category'];
        $key = $row['key_name'];
        $val = $row['value'];
        
        if (isset($config[$cat])) {
            $config[$cat][$key] = $val;
        }
    }
}

echo json_encode($config);
