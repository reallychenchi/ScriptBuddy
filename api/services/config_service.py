from api.db import query_all

class ConfigService:
    @staticmethod
    def get_all_configs():
        """从数据库加载所有配置"""
        sql = "SELECT category, key_name, value FROM script_configs"
        rows = query_all(sql)
        
        config = {
            "asr": {},
            "tts": {},
            "llm": {}
        }
        
        for row in rows:
            cat = row['category']
            key = row['key_name']
            val = row['value']
            
            if cat in config:
                config[cat][key] = val
                
        return config

    @staticmethod
    def get_public_config():
        """只返回前端需要的配置 (DeepSeek)，隐藏 VolcEngine Key"""
        full_config = ConfigService.get_all_configs()
        return {
            "llm": full_config.get("llm", {})
        }
