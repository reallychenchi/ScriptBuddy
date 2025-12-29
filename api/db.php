<?php
// api/db.php

// 数据库配置
$db_host = 'localhost'; // 推荐使用 localhost，如果不行再尝试 sql.m232.vhostgo.com
$db_name = 'chenchitest68';
$db_user = 'chenchitest68';
$db_pass = 'ccIhh10000';
$db_charset = 'utf8mb4';

// 创建 MySQLi 连接 (兼容 PHP 5.4+)
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);

// 检查连接
if ($conn->connect_error) {
    // 生产环境建议记录日志而不是直接输出错误
    die("Connection failed: " . $conn->connect_error);
}

// 设置字符集
$conn->set_charset($db_charset);

/**
 * 助手函数：执行查询并返回关联数组列表
 */
function db_query_all($sql) {
    global $conn;
    $result = $conn->query($sql);
    if (!$result) {
        return [];
    }
    
    $rows = [];
    while($row = $result->fetch_assoc()) {
        $rows[] = $row;
    }
    return $rows;
}
