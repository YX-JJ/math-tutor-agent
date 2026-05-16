from flask import Blueprint, render_template, request, jsonify
from services.prompt_builder import get_builder
from services.conversation_manager import get_manager
from services.deepseek_client import get_client
from storage.json_store import get_store
from config import get_config, MATH_TOPICS
import datetime
import re
import sys, os

def _debug(msg):
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'debug.log')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")

student_bp = Blueprint('student', __name__)


def get_student(student_id):
    data = get_store().read('students.json')
    for s in data.get('students', []):
        if s['id'] == student_id:
            return s
    return None


def save_student(student):
    store = get_store()
    data = store.read('students.json')
    for i, s in enumerate(data.get('students', [])):
        if s['id'] == student['id']:
            data['students'][i] = student
            store.write('students.json', data)
            return True
    return False


def _detect_verdict(ai_response):
    """Detect if AI marked the answer as correct or wrong.
    Primary: explicit marker [判定: 正确/错误]
    Fallback: check first line for common patterns."""
    # Primary: explicit marker (supports full-width colon and flexible spacing)
    m = re.search(r'\[判定[:：]\s*(正确|错误)\]', ai_response)
    if m:
        return m.group(1)
    # Fallback: check first 80 chars for obvious judgment patterns
    head = ai_response[:80]
    if re.search(r'(答对|正确|很棒|没错|做对|✓|✅|完全正确|答案正确)', head):
        return '正确'
    if re.search(r'(不对|错误|不正确|再想想|有误|✗|❌|错了|不对哦)', head):
        return '错误'
    return None


def _mark_problem_result(problem_id, is_correct, student_answer=''):
    """Mark a generated problem as correct/incorrect.
    Returns True if this is the first time the result is recorded (first answer)."""
    store = get_store()
    data = store.read('problem_bank.json')
    for p in data.get('problems', []):
        if p['id'] == problem_id:
            is_first = not p.get('student_attempted')
            p['student_attempted'] = True
            p['student_correct'] = is_correct
            if student_answer:
                p['student_answer'] = student_answer
            store.write('problem_bank.json', data)
            return is_first
    return True  # problem not found, treat as first


def _delete_problem(problem_id):
    """Remove a problem from the problem bank."""
    store = get_store()
    data = store.read('problem_bank.json')
    data['problems'] = [p for p in data.get('problems', []) if p['id'] != problem_id]
    store.write('problem_bank.json', data)


# Error reason categories (≤10 chars each)
_ERROR_CATEGORIES = [
    ('计算错误', ['计算', '算错', '算出来', '得数', '结果不对', '数值', '算出']),
    ('符号错误', ['符号', '正负', '负号', '正号', '变号', '移项', '去括号']),
    ('概念不清', ['概念', '定义', '不理解', '混淆', '记错', '没掌握']),
    ('公式用错', ['公式', '定理', '用错', '记错公式']),
    ('审题不清', ['审题', '看错', '漏看', '没注意', '忽略', '题目', '条件']),
    ('步骤缺失', ['步骤', '漏了', '没写', '不完整', '缺少', '跳过']),
    ('单位错误', ['单位', '厘米', '米', '度', '°']),
    ('逻辑错误', ['逻辑', '推理', '思路', '方法', '做法', '过程']),
]


def _categorize_reason(ai_response, student_answer):
    """Categorize error reason into a short label (≤10 chars)."""
    text = (ai_response or '') + ' ' + (student_answer or '')
    for category, keywords in _ERROR_CATEGORIES:
        for kw in keywords:
            if kw in text:
                return category
    return '答案错误'


def _tag_problem_reason(problem_id, ai_response, student_answer):
    """Tag a problem in the bank with error reason category."""
    category = _categorize_reason(ai_response, student_answer)
    store = get_store()
    data = store.read('problem_bank.json')
    for p in data.get('problems', []):
        if p['id'] == problem_id:
            # Merge with existing category if similar
            existing = p.get('reason_category', '')
            if existing and existing != category:
                # Keep existing if already categorized
                pass
            else:
                p['reason_category'] = category
            store.write('problem_bank.json', data)
            return


def _extract_wrong_reason(ai_response, student_answer, correct_answer):
    """Extract a brief wrong reason from AI response."""
    if ai_response:
        # Remove verdict marker
        text = re.sub(r'\[判定[:：]\s*(正确|错误)\]\s*', '', ai_response, count=1)
        # Try to extract first meaningful sentence (up to ~80 chars)
        # Look for patterns like "问题在于..." "错误原因是..." "你..." etc.
        sentences = re.split(r'[。；\n]', text)
        for s in sentences:
            s = s.strip()
            # Skip empty, greeting, or encouraging-only sentences
            if not s or len(s) < 4:
                continue
            if re.match(r'^(你好|很棒|不错|加油|继续|没关系|没关系哦|别灰心|你可以的|我们先|我们来|让我|首先)', s):
                continue
            # Take first substantive sentence, truncate to 80 chars
            if len(s) > 80:
                s = s[:80] + '...'
            return s
    # Fallback: simple comparison
    if student_answer and correct_answer:
        return f'学生答"{student_answer}"，正确答案是"{correct_answer}"'
    return '答案错误'


def _add_wrong_problem_from_generated(problem, student, student_answer, ai_response=''):
    """Add a generated problem to wrong_problems.json if answered incorrectly."""
    store = get_store()
    wp_data = store.read('wrong_problems.json')
    # Check if already exists — update instead of duplicating
    reason = _extract_wrong_reason(ai_response, student_answer, problem.get('answer', ''))
    for w in wp_data.get('wrong_problems', []):
        if w.get('student_id') == student['id'] and w.get('question', '').strip() == problem.get('question', '').strip():
            w['student_answer'] = student_answer
            w['reason'] = reason
            w['updated_at'] = datetime.datetime.now().isoformat()
            store.write('wrong_problems.json', wp_data)
            return
    wp_id = store.generate_id('wrong_problems.json')
    wp_data = store.read('wrong_problems.json')
    new_wp = {
        "id": wp_id,
        "student_id": student['id'],
        "student_name": student.get('name', ''),
        "question": problem.get('question', ''),
        "answer": problem.get('answer', ''),
        "student_answer": student_answer,
        "topic": problem.get('topic', ''),
        "difficulty": problem.get('difficulty', 3),
        "solution_steps": '\n'.join(problem.get('solution_steps', [])) if isinstance(problem.get('solution_steps'), list) else problem.get('solution_steps', ''),
        "hints": '\n'.join(problem.get('hints', [])) if isinstance(problem.get('hints'), list) else problem.get('hints', ''),
        "reason": reason,
        "created_at": datetime.datetime.now().isoformat(),
    }
    wp_data['wrong_problems'].append(new_wp)
    store.write('wrong_problems.json', wp_data)


@student_bp.route('/chat/<student_id>')
def chat(student_id):
    student = get_student(student_id)
    if not student:
        return render_template('error.html', code=404, message='学生未找到'), 404

    manager = get_manager()
    problem_id = request.args.get('problem_id', '')
    topic_focus = request.args.get('topic', '')
    active_session_id = request.args.get('session_id')

    # If a problem is specified, start a session with it
    if problem_id:
        problem_data = get_store().read('problem_bank.json')
        problem = None
        for p in problem_data.get('problems', []):
            if p['id'] == problem_id:
                problem = p
                break
        if problem:
            # Reset attempted flag for fresh session
            problem['student_attempted'] = False
            problem.pop('student_answer', None)
            problem.pop('student_correct', None)
            get_store().write('problem_bank.json', problem_data)

            topic_focus = problem.get('topic', topic_focus)
            session_id = manager.start_session(student_id, topic_focus, problem_id=problem_id)
            # Post the problem as the first AI message
            first_msg = f"🔔 请先尝试回答以下题目，然后再看解答：\n\n**{problem['question']}**"
            manager.save_message(session_id, 'assistant', first_msg, {'problem_id': problem_id})
            active_session_id = session_id

    sessions = manager.get_sessions(student_id)

    return render_template('student_chat.html',
                           student=student,
                           sessions=sessions,
                           active_session_id=active_session_id,
                           topic_focus=topic_focus,
                           topics=MATH_TOPICS)


@student_bp.route('/chat/<student_id>/message', methods=['POST'])
def send_message(student_id):
    student = get_student(student_id)
    if not student:
        return jsonify({"error": "学生未找到"}), 404

    data = request.get_json()
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', '')
    topic_focus = data.get('topic', '')

    _debug(f"[DEBUG]send_message called: student={student_id}, session={session_id}, msg_len={len(user_message)}\n")

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    manager = get_manager()

    # Auto-create a new session if none exists
    if not session_id:
        session_id = manager.start_session(student_id, topic_focus)
        manager.save_message(session_id, 'system',
                             f"开始与{student['name']}的辅导对话" + (f"（重点：{topic_focus}）" if topic_focus else ""))

    # Save user message
    manager.save_message(session_id, 'user', user_message)

    # Build messages and call AI
    builder = get_builder()
    cfg = get_config()
    history = manager.get_recent_messages(student_id, cfg.get('max_history_messages', 20))
    history = history[:-1]  # Exclude the message we just saved (it's the new_message)
    messages = builder.build_chat_messages(student, history, user_message)

    client = get_client()
    result = client.chat_with_retry(
        messages,
        temperature=cfg.get('temperature_tutoring', 0.7),
        max_tokens=cfg.get('max_tokens', 2048)
    )

    # Save AI response
    metadata = {
        "tokens_used": result.get('tokens_used', 0),
        "model": cfg.get('model', 'deepseek-chat'),
    }
    manager.save_message(session_id, 'assistant', result['content'], metadata)

    # Detect if student was answering a generated problem and track result
    ai_response = result['content']
    verdict = _detect_verdict(ai_response)
    _debug(f"[DEBUG]verdict={verdict}, session_id={session_id}\n")
    if verdict:
        session = manager.get_session(session_id)
        problem_id = session.get('problem_id', '') if session else ''
        _debug(f"[DEBUG]problem_id={problem_id}\n")
        if problem_id:
            is_correct = (verdict == '正确')
            is_first = _mark_problem_result(problem_id, is_correct, user_message)
            _debug(f"[DEBUG]is_correct={is_correct}, is_first={is_first}\n")
            if not is_correct:
                problem_data = get_store().read('problem_bank.json')
                for p in problem_data.get('problems', []):
                    if p['id'] == problem_id:
                        _add_wrong_problem_from_generated(p, student, user_message, ai_response)
                        break
            # Only increment stats on first answer (not on re-answers)
            if is_first:
                student['total_problems_attempted'] = student.get('total_problems_attempted', 0) + 1
                total = student['total_problems_attempted']
                old_correct = int((student.get('overall_accuracy', 0) or 0) * (total - 1)) if total > 1 else 0
                new_correct = old_correct + (1 if is_correct else 0)
                student['overall_accuracy'] = round(new_correct / total, 4)
                save_student(student)
                if is_correct:
                    _debug(f"[DEBUG]Deleting problem {problem_id}\n")
                    _delete_problem(problem_id)
                else:
                    _debug(f"[DEBUG]Tagging problem {problem_id}\n")
                    _tag_problem_reason(problem_id, ai_response, user_message)
        else:
            _debug("[DEBUG] No problem_id in session, skipping\n")
    else:
        _debug("[DEBUG] No verdict detected, skipping\n")

    # Auto-analyze and update mastery after every 6 messages (3 exchanges)
    session = manager.get_session(session_id)
    msg_count = len(session.get('messages', [])) if session else 0
    if msg_count >= 6 and msg_count % 6 == 0:
        try:
            from services.student_profiler import get_profiler
            profiler = get_profiler()
            profiler.analyze_and_update(student_id)
        except Exception:
            pass  # Don't block chat if analysis fails

    return jsonify({
        "response": ai_response,
        "session_id": session_id,
        "tokens_used": result.get('tokens_used', 0),
    })


@student_bp.route('/history/<student_id>')
def history(student_id):
    student = get_student(student_id)
    if not student:
        return jsonify({"error": "学生未找到"}), 404

    manager = get_manager()
    sessions = manager.get_sessions(student_id)
    return jsonify({"student_name": student['name'], "sessions": sessions})


@student_bp.route('/session/<session_id>/messages')
def session_messages(session_id):
    manager = get_manager()
    session = manager.get_session(session_id)
    if not session:
        return jsonify({"error": "会话未找到"}), 404
    messages = [m for m in session.get('messages', []) if m['role'] != 'system']
    return jsonify({"messages": messages})
