# ScriptBuddy 服务端 API 接口文档

> 版本: 2.0
> 后端: Python (FastAPI) + SQLite
> 基础路径: `/api/`
> 数据格式: JSON (UTF-8)

---

## 1. 获取系统配置

获取 LLM 服务的配置信息（仅返回前端需要的配置，ASR/TTS 配置保留在服务端）。

**请求**
```
GET /api/config
```

**响应**
```json
{
  "llm": {
    "apiKey": "sk-903a962786f34773a1680f6fb6fad64d",
    "baseUrl": "https://api.deepseek.com"
  }
}
```

**说明**:
- ASR/TTS 配置保留在服务端，通过 WebSocket 代理使用
- 仅返回前端直接需要的 LLM 配置
- **数据来源**: `script_configs` 表

---

## 2. 获取剧本内容

获取指定剧本的元数据和台词列表。

**请求**
```
GET /api/script?id={story_id}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 否 | 剧本ID，默认为 `1` |

**响应**
```json
{
  "meta": {
    "title": "面试练习：自我介绍",
    "description": "模拟一场简单的HR面试场景。",
    "roleMap": {
      "甲": "面试官",
      "乙": "求职者",
      "合": "旁白/系统"
    }
  },
  "lines": [
    {
      "id": 1,
      "role": "甲",
      "content": "您好，请先简单做一个自我介绍吧。",
      "duration": 3000
    },
    {
      "id": 2,
      "role": "乙",
      "content": "好的。面试官您好，我叫陈驰，是一名全栈工程师。",
      "duration": 4000
    }
  ]
}
```

**错误响应** (404)
```json
{
  "error": "Script not found"
}
```

**数据来源**: `script_stories` + `script_lines` 表

---

## 3. WebSocket 代理端点

### 3.1 ASR 语音识别代理

**端点**
```
WebSocket: /api/ws/asr
```

**说明**:
- 前端通过此 WebSocket 连接进行语音识别
- 服务端自动注入 VolcEngine 认证信息
- 支持 GZIP 压缩

### 3.2 TTS 语音合成代理

**端点**
```
WebSocket: /api/ws/tts
```

**说明**:
- 前端通过此 WebSocket 连接进行语音合成
- 服务端自动注入 VolcEngine 认证信息

---

## 4. 后台管理 API

### 4.1 添加台词

**请求**
```
POST /api/admin
Content-Type: application/json

{
  "action": "add",
  "story_id": 1,
  "role": "甲",
  "content": "台词内容",
  "duration": 3000,
  "sort": 1
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | ✓ | 固定值 `add` |
| role | string | ✓ | 角色标识: `甲` / `乙` / `合` |
| content | string | ✓ | 台词内容 |
| duration | int | 否 | 时长(毫秒)，默认 3000 |
| sort | int | ✓ | 排序号 |

### 3.2 更新台词

**请求**
```
POST /api/admin.php
Content-Type: application/x-www-form-urlencoded

action=update&id=1&role=甲&content=新台词&duration=3000&sort=1
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | ✓ | 固定值 `update` |
| id | int | ✓ | 台词ID |
| role | string | ✓ | 角色标识 |
| content | string | ✓ | 台词内容 |
| duration | int | 否 | 时长(毫秒) |
| sort | int | ✓ | 排序号 |

### 3.3 删除台词

**请求**
```
POST /api/admin.php
Content-Type: application/x-www-form-urlencoded

action=delete&id=1
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | ✓ | 固定值 `delete` |
| id | int | ✓ | 台词ID |

---

## 数据库表结构 (SQLite)

### script_configs
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 (自增) |
| category | VARCHAR(50) | 分类: asr/tts/llm |
| key_name | VARCHAR(50) | 键名 |
| value | VARCHAR(500) | 键值 |

**索引**: UNIQUE(category, key_name)

### script_stories
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 (自增) |
| title | VARCHAR(100) | 剧本标题 |
| description | VARCHAR(255) | 剧本描述 |
| role_map_json | TEXT | 角色映射 JSON |
| created_at | TIMESTAMP | 创建时间 |

### script_lines
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 (自增) |
| story_id | INTEGER | 关联剧本ID |
| role_key | VARCHAR(50) | 角色标识 |
| content | TEXT | 台词内容 |
| duration_ms | INTEGER | 预估时长(毫秒) |
| sort_order | INTEGER | 排序号 |

**索引**: INDEX idx_story_order(story_id, sort_order)
**外键**: FOREIGN KEY (story_id) REFERENCES script_stories(id)

---

## 依赖文件

| 文件 | 说明 |
|------|------|
| `api/db.py` | 数据库连接模块 (SQLite) |
| `api/init_db.py` | 数据库初始化脚本 |
| `database.sql` | 数据库结构 SQL 文件 |

**初始化数据库**:
```bash
python3 api/init_db.py
```

**数据库位置**: `scriptbuddy.db` (项目根目录)
