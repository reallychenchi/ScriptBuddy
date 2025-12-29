import json
from api.db import query_all, execute_query

class ScriptService:
    @staticmethod
    def get_script_by_id(story_id):
        # 1. Meta
        sql_story = "SELECT * FROM script_stories WHERE id = %s LIMIT 1"
        stories = query_all(sql_story, (story_id,))
        if not stories:
            return None
        story = stories[0]

        # 2. Lines
        sql_lines = "SELECT * FROM script_lines WHERE story_id = %s ORDER BY sort_order ASC"
        lines = query_all(sql_lines, (story_id,))

        output_lines = []
        for line in lines:
            output_lines.append({
                "id": line['id'],
                "role": line['role_key'],
                "content": line['content'],
                "duration": line['duration_ms']
            })

        return {
            "meta": {
                "title": story['title'],
                "description": story['description'],
                "roleMap": json.loads(story['role_map_json']) if story['role_map_json'] else {}
            },
            "lines": output_lines
        }

    @staticmethod
    def add_line(data):
        sql = "INSERT INTO script_lines (story_id, role_key, content, duration_ms, sort_order) VALUES (%s, %s, %s, %s, %s)"
        execute_query(sql, (data.story_id, data.role, data.content, data.duration, data.sort))

    @staticmethod
    def update_line(data):
        sql = "UPDATE script_lines SET role_key=%s, content=%s, duration_ms=%s, sort_order=%s WHERE id=%s"
        execute_query(sql, (data.role, data.content, data.duration, data.sort, data.id))

    @staticmethod
    def delete_line(line_id):
        sql = "DELETE FROM script_lines WHERE id=%s"
        execute_query(sql, (line_id,))
