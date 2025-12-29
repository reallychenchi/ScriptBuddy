<?php
// api/admin.php
require_once 'db.php';

// 简单的防乱码头
header('Content-Type: text/html; charset=utf-8');

// 获取当前剧本ID (默认1)
$story_id = isset($_GET['story_id']) ? intval($_GET['story_id']) : 1;

// --- 逻辑处理部分 ---

$action = isset($_POST['action']) ? $_POST['action'] : '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if ($action === 'add') {
        $role = $_POST['role'];
        $content = $_POST['content'];
        $duration = intval($_POST['duration']);
        $sort = intval($_POST['sort']);
        
        $stmt = $conn->prepare("INSERT INTO script_lines (story_id, role_key, content, duration_ms, sort_order) VALUES (?, ?, ?, ?, ?)");
        $stmt->bind_param("issii", $story_id, $role, $content, $duration, $sort);
        $stmt->execute();
        $stmt->close();
        
    } elseif ($action === 'delete') {
        $id = intval($_POST['id']);
        $conn->query("DELETE FROM script_lines WHERE id = $id");
        
    } elseif ($action === 'update') {
        $id = intval($_POST['id']);
        $role = $_POST['role'];
        $content = $_POST['content'];
        $duration = intval($_POST['duration']);
        $sort = intval($_POST['sort']);
        
        $stmt = $conn->prepare("UPDATE script_lines SET role_key=?, content=?, duration_ms=?, sort_order=? WHERE id=?");
        $stmt->bind_param("ssiii", $role, $content, $duration, $sort, $id);
        $stmt->execute();
        $stmt->close();
    }
    
    // PRG模式防止重复提交
    header("Location: admin.php?story_id=$story_id");
    exit;
}

// --- 数据查询部分 ---

// 查剧本信息
$storyRes = $conn->query("SELECT * FROM script_stories WHERE id = $story_id");
$story = $storyRes->fetch_assoc();

// 查台词列表
$linesRes = $conn->query("SELECT * FROM script_lines WHERE story_id = $story_id ORDER BY sort_order ASC");
$lines = [];
if ($linesRes) {
    while($row = $linesRes->fetch_assoc()) {
        $lines[] = $row;
    }
}
?>

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScriptBuddy 后台管理</title>
    <link href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/4.6.2/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; background-color: #f8f9fa; }
        .card { margin-bottom: 20px; }
        .action-btn { margin-right: 5px; }
    </style>
</head>
<body>

<div class="container">
    <div class="row">
        <div class="col-md-12">
            <h1 class="mb-4">🎬 剧本管理: <?php echo htmlspecialchars($story['title']); ?></h1>
            <p class="text-muted"><?php echo htmlspecialchars($story['description']); ?></p>
            
            <!-- 添加台词表单 -->
            <div class="card">
                <div class="card-header bg-primary text-white">
                    ➕ 追加新台词
                </div>
                <div class="card-body">
                    <form method="POST" class="form-inline">
                        <input type="hidden" name="action" value="add">
                        
                        <input type="number" name="sort" class="form-control mb-2 mr-sm-2" placeholder="排序" style="width: 80px;" required value="<?php echo count($lines) + 1; ?>">
                        
                        <select name="role" class="form-control mb-2 mr-sm-2">
                            <option value="甲">甲 (面试官)</option>
                            <option value="乙">乙 (求职者)</option>
                            <option value="合">合 (旁白)</option>
                        </select>
                        
                        <input type="text" name="content" class="form-control mb-2 mr-sm-2" style="width: 400px;" placeholder="台词内容" required>
                        
                        <input type="number" name="duration" class="form-control mb-2 mr-sm-2" placeholder="时长(ms)" value="3000">
                        
                        <button type="submit" class="btn btn-success mb-2">添加</button>
                    </form>
                </div>
            </div>

            <!-- 台词列表 -->
            <div class="card">
                <div class="card-header">
                    📜 台词列表
                </div>
                <div class="card-body p-0">
                    <table class="table table-striped table-hover mb-0">
                        <thead class="thead-dark">
                            <tr>
                                <th style="width: 60px;">排序</th>
                                <th style="width: 100px;">角色</th>
                                <th>内容</th>
                                <th style="width: 100px;">时长(ms)</th>
                                <th style="width: 150px;">操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($lines as $line): ?>
                            <tr>
                                <form method="POST">
                                    <input type="hidden" name="action" value="update">
                                    <input type="hidden" name="id" value="<?php echo $line['id']; ?>">
                                    
                                    <td>
                                        <input type="number" name="sort" class="form-control form-control-sm" value="<?php echo $line['sort_order']; ?>">
                                    </td>
                                    <td>
                                        <select name="role" class="form-control form-control-sm">
                                            <option value="甲" <?php if($line['role_key'] == '甲') echo 'selected'; ?>>甲</option>
                                            <option value="乙" <?php if($line['role_key'] == '乙') echo 'selected'; ?>>乙</option>
                                            <option value="合" <?php if($line['role_key'] == '合') echo 'selected'; ?>>合</option>
                                        </select>
                                    </td>
                                    <td>
                                        <input type="text" name="content" class="form-control form-control-sm" value="<?php echo htmlspecialchars($line['content']); ?>">
                                    </td>
                                    <td>
                                        <input type="number" name="duration" class="form-control form-control-sm" value="<?php echo $line['duration_ms']; ?>">
                                    </td>
                                    <td>
                                        <button type="submit" class="btn btn-sm btn-primary action-btn">保存</button>
                                        <button type="button" class="btn btn-sm btn-danger action-btn" onclick="deleteLine(<?php echo $line['id']; ?>)">删除</button>
                                    </td>
                                </form>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
            
        </div>
    </div>
</div>

<!-- 删除确认表单 -->
<form id="deleteForm" method="POST" style="display:none;">
    <input type="hidden" name="action" value="delete">
    <input type="hidden" name="id" id="deleteId">
</form>

<script>
function deleteLine(id) {
    if (confirm('确认删除这句台词吗？')) {
        document.getElementById('deleteId').value = id;
        document.getElementById('deleteForm').submit();
    }
}
</script>

</body>
</html>
