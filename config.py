import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')

_config = None

def _load_config():
    config_path = os.path.join(STORAGE_DIR, 'system_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_config():
    global _config
    if _config is None:
        _config = _load_config()
    return _config

def save_config(cfg):
    global _config
    config_path = os.path.join(STORAGE_DIR, 'system_config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    _config = cfg

def reload_config():
    global _config
    _config = _load_config()
    return _config

def get_deepseek_api_key():
    return get_config().get('deepseek_api_key', '')

def get_deepseek_api_base():
    return get_config().get('deepseek_api_base', 'https://api.deepseek.com/v1')

def get_model():
    return get_config().get('model', 'deepseek-chat')

def get_secret_key():
    return get_config().get('secret_key', 'dev-secret-change-me')

MATH_TOPICS = [
    {"id": "linear_equations", "name": "一元一次方程", "category": "algebra"},
    {"id": "linear_inequalities", "name": "一元一次不等式", "category": "algebra"},
    {"id": "systems_of_equations", "name": "二元一次方程组", "category": "algebra"},
    {"id": "linear_functions", "name": "一次函数", "category": "algebra"},
    {"id": "polynomial_operations", "name": "整式运算", "category": "algebra"},
    {"id": "factoring", "name": "因式分解", "category": "algebra"},
    {"id": "fractions", "name": "分式", "category": "algebra"},
    {"id": "quadratic_roots", "name": "二次根式", "category": "algebra"},
    {"id": "triangles", "name": "三角形", "category": "geometry"},
    {"id": "quadrilaterals", "name": "四边形", "category": "geometry"},
    {"id": "circles", "name": "圆", "category": "geometry"},
    {"id": "probability", "name": "概率", "category": "statistics"},
    {"id": "statistics", "name": "统计", "category": "statistics"},
    {"id": "coordinate_geometry", "name": "平面直角坐标系", "category": "geometry"},
]
