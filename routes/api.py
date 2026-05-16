from flask import Blueprint, request, jsonify, session
from functools import wraps
from storage.json_store import get_store
from services.prompt_builder import get_builder
from services.deepseek_client import get_client
from services.conversation_manager import get_manager
from services.student_profiler import get_profiler
from services.problem_generator import get_generator
from config import get_config, MATH_TOPICS
import datetime

api_bp = Blueprint('api', __name__)


def _check_auth():
    return session.get('teacher_logged_in')


def _require_auth():
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401


@api_bp.route('/students')
def get_students():
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401
    data = get_store().read('students.json')
    return jsonify({"students": data.get('students', [])})


@api_bp.route('/students/<student_id>/profile')
def get_student_profile(student_id):
    data = get_store().read('students.json')
    for s in data.get('students', []):
        if s['id'] == student_id:
            return jsonify({"profile": s})
    return jsonify({"error": "学生未找到"}), 404


@api_bp.route('/students/<student_id>/weakness/update', methods=['POST'])
def update_weakness(student_id):
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401
    data = get_store().read('students.json')
    student = None
    for s in data.get('students', []):
        if s['id'] == student_id:
            student = s
            break
    if not student:
        return jsonify({"error": "学生未找到"}), 404

    req_data = request.get_json()
    weaknesses = req_data.get('weaknesses', student.get('weaknesses', []))
    student['weaknesses'] = weaknesses
    student['updated_at'] = datetime.datetime.now().isoformat()
    get_store().write('students.json', data)
    return jsonify({"success": True})


@api_bp.route('/students/<student_id>/stats')
def get_student_stats(student_id):
    data = get_store().read('students.json')
    for s in data.get('students', []):
        if s['id'] == student_id:
            return jsonify({
                "mastery_levels": s.get('mastery_levels', {}),
                "overall_accuracy": s.get('overall_accuracy', 0),
                "total_problems_attempted": s.get('total_problems_attempted', 0),
                "weaknesses": s.get('weaknesses', []),
                "strengths": s.get('strengths', []),
            })
    return jsonify({"error": "学生未找到"}), 404


@api_bp.route('/problems/generate/<student_id>', methods=['POST'])
def generate_problem(student_id):
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401

    data = get_store().read('students.json')
    student = None
    for s in data.get('students', []):
        if s['id'] == student_id:
            student = s
            break
    if not student:
        return jsonify({"error": "学生未找到"}), 404

    req_data = request.get_json() or {}
    topic = req_data.get('topic', 'linear_equations')
    difficulty = int(req_data.get('difficulty', 3))

    generator = get_generator()
    result = generator.generate_problem(student, topic, difficulty)

    if result:
        return jsonify({"success": True, "problem": result})
    else:
        return jsonify({"error": "题目生成失败，请重试"}), 500


@api_bp.route('/problems/latest/<student_id>')
def get_latest_problems(student_id):
    data = get_store().read('problem_bank.json')
    problems = [p for p in data.get('problems', [])
                if p.get('generated_for_student') == student_id]
    problems.sort(key=lambda p: p.get('created_at', ''), reverse=True)
    return jsonify({"problems": problems[:10]})


@api_bp.route('/sessions/<student_id>/analyze', methods=['POST'])
def analyze_sessions(student_id):
    """Trigger weakness analysis for a student based on recent conversations."""
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401

    profiler = get_profiler()
    result = profiler.analyze_student(student_id)
    return jsonify(result)


@api_bp.route('/students/<student_id>/weakness/auto_update', methods=['POST'])
def auto_update_weakness(student_id):
    """Auto analyze and update student weaknesses based on conversation history."""
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401

    profiler = get_profiler()
    result = profiler.analyze_and_update(student_id)
    return jsonify(result)


@api_bp.route('/students/<student_id>/notes', methods=['POST'])
def update_teacher_notes(student_id):
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401
    data = get_store().read('students.json')
    student = None
    for s in data.get('students', []):
        if s['id'] == student_id:
            student = s
            break
    if not student:
        return jsonify({"error": "学生未找到"}), 404

    req_data = request.get_json()
    student['teacher_notes'] = req_data.get('notes', '')
    student['updated_at'] = datetime.datetime.now().isoformat()
    get_store().write('students.json', data)
    return jsonify({"success": True})


@api_bp.route('/students/<student_id>/reset_stats', methods=['POST'])
def reset_student_stats(student_id):
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401
    data = get_store().read('students.json')
    student = None
    for s in data.get('students', []):
        if s['id'] == student_id:
            student = s
            break
    if not student:
        return jsonify({"error": "学生未找到"}), 404

    # Reset mastery levels to 0
    for topic in student.get('mastery_levels', {}):
        student['mastery_levels'][topic] = 0
    # Reset problem stats
    student['total_problems_attempted'] = 0
    student['overall_accuracy'] = 0
    # Clear analyzed sessions so they can be re-analyzed
    student['analyzed_sessions'] = {}
    student['updated_at'] = datetime.datetime.now().isoformat()
    get_store().write('students.json', data)
    # Also reset problem tracking in problem_bank.json
    pb_data = get_store().read('problem_bank.json')
    for p in pb_data.get('problems', []):
        if p.get('generated_for_student') == student_id:
            p['student_attempted'] = False
            p['student_correct'] = False
    get_store().write('problem_bank.json', pb_data)
    return jsonify({"success": True})


@api_bp.route('/config', methods=['GET', 'POST'])
def config():
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401

    from config import get_config, save_config

    if request.method == 'POST':
        cfg = get_config()
        req_data = request.get_json()
        if 'deepseek_api_key' in req_data:
            cfg['deepseek_api_key'] = req_data['deepseek_api_key']
        if 'model' in req_data:
            cfg['model'] = req_data['model']
        save_config(cfg)
        return jsonify({"success": True})

    cfg = get_config()
    return jsonify({
        "deepseek_api_key": cfg.get('deepseek_api_key', '')[:8] + '***',
        "model": cfg.get('model', 'deepseek-chat'),
    })


@api_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401
    data = get_store().read('conversations.json')
    before = len(data.get('conversations', []))
    data['conversations'] = [c for c in data.get('conversations', []) if c['id'] != session_id]
    after = len(data['conversations'])
    if after < before:
        get_store().write('conversations.json', data)
        return jsonify({"success": True})
    return jsonify({"error": "会话未找到"}), 404


@api_bp.route('/problems/<problem_id>', methods=['DELETE'])
def delete_problem(problem_id):
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401
    data = get_store().read('problem_bank.json')
    before = len(data.get('problems', []))
    data['problems'] = [p for p in data.get('problems', []) if p['id'] != problem_id]
    after = len(data['problems'])
    if after < before:
        get_store().write('problem_bank.json', data)
        return jsonify({"success": True})
    return jsonify({"error": "题目未找到"}), 404


@api_bp.route('/students/<student_id>/sessions', methods=['DELETE'])
def delete_student_sessions(student_id):
    if not _check_auth():
        return jsonify({"error": "未登录"}), 401
    data = get_store().read('conversations.json')
    before = len(data.get('conversations', []))
    data['conversations'] = [c for c in data.get('conversations', []) if c.get('student_id') != student_id]
    after = len(data['conversations'])
    get_store().write('conversations.json', data)
    return jsonify({"success": True, "deleted": before - after})
