-- 数据库结构与演示数据
-- 对应项目：ScriptBuddy
-- 运行环境：SQLite 3

-- 1. 配置表 (script_configs)
-- 用于存储 ASR, TTS, LLM 的各类 Key 和 Secret
DROP TABLE IF EXISTS script_configs;
CREATE TABLE script_configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category VARCHAR(50) NOT NULL DEFAULT '',
  key_name VARCHAR(50) NOT NULL DEFAULT '',
  value VARCHAR(500) NOT NULL DEFAULT '',
  UNIQUE(category, key_name)
);

-- 插入默认配置数据
INSERT INTO script_configs (category, key_name, value) VALUES
('asr', 'appId', '5349866810'),
('asr', 'token', 'j_DA2hGKCvrytiS1fM-1jN5Cqz6Mxpx3'),
('asr', 'secret', '1oJHD2KkFJTMbLgPIx4fAR9XS7qGZNM7'),
('asr', 'cluster', 'volc_auction_streaming_2.0'),

('tts', 'appId', '5349866810'),
('tts', 'token', 'j_DA2hGKCvrytiS1fM-1jN5Cqz6Mxpx3'),
('tts', 'secret', '1oJHD2KkFJTMbLgPIx4fAR9XS7qGZNM7'),
('tts', 'cluster', 'volcano_tts'),
('tts', 'voiceType', 'zh_male_linjiananhai_moon_bigtts'),

('llm', 'apiKey', 'sk-903a962786f34773a1680f6fb6fad64d'),
('llm', 'baseUrl', 'https://api.deepseek.com');


-- 2. 剧本元数据表 (script_stories)
-- 存储剧本标题、描述和角色映射
DROP TABLE IF EXISTS script_stories;
CREATE TABLE script_stories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title VARCHAR(100) NOT NULL DEFAULT '',
  description VARCHAR(255) DEFAULT '',
  role_map_json TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入演示剧本
INSERT INTO script_stories (id, title, description, role_map_json) VALUES
(1, '面试练习：自我介绍', '模拟一场简单的HR面试场景。', '{"甲":"面试官","乙":"求职者","合":"旁白/系统"}');


-- 3. 剧本台词表 (script_lines)
-- 存储具体的台词内容
DROP TABLE IF EXISTS script_lines;
CREATE TABLE script_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  story_id INTEGER NOT NULL,
  role_key VARCHAR(50) NOT NULL DEFAULT '',
  content TEXT NOT NULL,
  duration_ms INTEGER DEFAULT 3000,
  sort_order INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (story_id) REFERENCES script_stories(id)
);

CREATE INDEX idx_story_order ON script_lines(story_id, sort_order);

-- 插入演示台词 (对应 script_stories id=1)
INSERT INTO script_lines (story_id, role_key, content, duration_ms, sort_order) VALUES
(1, '甲', '您好，请先简单做一个自我介绍吧。', 3000, 1),
(1, '乙', '好的。面试官您好，我叫陈驰，是一名全栈工程师。', 4000, 2),
(1, '甲', '我看你的简历上写着熟悉 React 和 PHP？', 3000, 3),
(1, '乙', '是的，我即使在 PHP 5.4 的环境下也能写出现代化的代码。', 4000, 4),
(1, '合', '（面试官露出了满意的微笑）', 2000, 5),
(1, '甲', '很有意思。那我们开始技术测试吧。', 3000, 6),
(1, '乙', '没问题，请出题。', 2000, 7);
