from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from functools import wraps
from storage.json_store import get_store
from services.conversation_manager import get_manager
from config import MATH_TOPICS
import datetime
import io


teacher_bp = Blueprint('teacher', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('teacher_logged_in'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@teacher_bp.route('/dashboard')
@login_required
def dashboard():
    store = get_store()
    students_data = store.read('students.json')
    students = students_data.get('students', [])

    # Calculate stats
    total_students = len(students)
    avg_accuracy = 0
    if total_students > 0:
        avg_accuracy = sum(s.get('overall_accuracy', 0) or 0 for s in students) / total_students * 100

    # Count active today
    today = datetime.date.today().isoformat()
    active_today = 0
    manager = get_manager()
    for s in students:
        sessions = manager.get_sessions(s['id'])
        for sess in sessions:
            if sess.get('session_start', '').startswith(today):
                active_today += 1
                break

    return render_template('teacher_dashboard.html',
                           students=students,
                           topics=MATH_TOPICS,
                           stats={
                               'total_students': total_students,
                               'avg_accuracy': round(avg_accuracy),
                               'active_today': active_today,
                           })


@teacher_bp.route('/student/<student_id>')
@login_required
def student_detail(student_id):
    store = get_store()
    students_data = store.read('students.json')
    student = None
    for s in students_data.get('students', []):
        if s['id'] == student_id:
            student = s
            break

    if not student:
        return render_template('error.html', code=404, message='学生未找到'), 404

    manager = get_manager()
    sessions = manager.get_sessions(student_id)

    # Get generated problems for this student
    problems_data = store.read('problem_bank.json')
    student_problems = [p for p in problems_data.get('problems', [])
                        if p.get('generated_for_student') == student_id]

    # Get wrong problems for this student
    wp_data = store.read('wrong_problems.json')
    student_wrong_problems = [w for w in wp_data.get('wrong_problems', [])
                              if w.get('student_id') == student_id]
    student_wrong_problems.sort(key=lambda w: w.get('created_at', ''), reverse=True)

    return render_template('teacher_student_detail.html',
                           student=student,
                           sessions=sessions,
                           problems=student_problems,
                           wrong_problems=student_wrong_problems,
                           topics=MATH_TOPICS)


@teacher_bp.route('/student/add', methods=['POST'])
@login_required
def add_student():
    name = request.form.get('name', '').strip()
    if not name:
        flash('学生姓名不能为空', 'error')
        return redirect(url_for('teacher.dashboard'))

    store = get_store()
    data = store.read('students.json')
    new_id = store.generate_id('students.json')
    data = store.read('students.json')

    student = {
        "id": new_id,
        "name": name,
        "grade": 8,
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "profile": {
            "learning_style": "未设置",
            "preferred_pace": "moderate",
            "attention_span_minutes": 25,
            "math_anxiety_level": "medium"
        },
        "weaknesses": [],
        "strengths": [],
        "mastery_levels": {},
        "total_problems_attempted": 0,
        "overall_accuracy": 0,
        "teacher_notes": "",
        "analyzed_sessions": {}
    }

    # Initialize mastery levels
    for topic in MATH_TOPICS:
        student['mastery_levels'][topic['id']] = 0

    data['students'].append(student)
    store.write('students.json', data)
    flash(f'学生 "{name}" 添加成功！', 'success')
    return redirect(url_for('teacher.student_detail', student_id=new_id))


@teacher_bp.route('/student/<student_id>/edit', methods=['POST'])
@login_required
def edit_student(student_id):
    store = get_store()
    data = store.read('students.json')
    student = None
    for s in data.get('students', []):
        if s['id'] == student_id:
            student = s
            break

    if not student:
        flash('学生未找到', 'error')
        return redirect(url_for('teacher.dashboard'))

    # Update profile
    student['name'] = request.form.get('name', student['name'])
    student['profile']['learning_style'] = request.form.get('learning_style', student['profile'].get('learning_style'))
    student['teacher_notes'] = request.form.get('teacher_notes', student.get('teacher_notes', ''))
    student['updated_at'] = datetime.datetime.now().isoformat()

    # Update mastery levels
    for topic in MATH_TOPICS:
        key = f"mastery_{topic['id']}"
        if key in request.form:
            try:
                val = int(request.form[key])
                student['mastery_levels'][topic['id']] = max(0, min(100, val))
            except ValueError:
                pass

    store.write('students.json', data)
    flash(f'学生 "{student["name"]}" 信息已更新', 'success')
    return redirect(url_for('teacher.student_detail', student_id=student_id))


@teacher_bp.route('/student/<student_id>/edit_weakness', methods=['POST'])
@login_required
def edit_weakness(student_id):
    """Add or update a weakness entry for a student."""
    store = get_store()
    data = store.read('students.json')
    student = None
    for s in data.get('students', []):
        if s['id'] == student_id:
            student = s
            break

    if not student:
        return jsonify({"error": "学生未找到"}), 404

    topic = request.form.get('topic', '')
    subtopic = request.form.get('subtopic', '')
    severity = int(request.form.get('severity', 5))
    evidence = request.form.get('evidence', '')

    # Check if weakness for this topic already exists
    existing = None
    for w in student.get('weaknesses', []):
        if w['topic'] == topic:
            existing = w
            break

    if existing:
        existing['subtopic'] = subtopic
        existing['severity'] = severity
        existing['evidence'] = evidence
        existing['last_assessed'] = datetime.date.today().isoformat()
    else:
        student['weaknesses'].append({
            "topic": topic,
            "subtopic": subtopic,
            "severity": severity,
            "last_assessed": datetime.date.today().isoformat(),
            "evidence": evidence,
            "problem_count_attempted": 0,
            "problem_count_correct": 0,
        })
        # New weakness: seed mastery_levels from severity so radar chart updates immediately
        # severity 1 → mastery 90, severity 5 → mastery 50, severity 10 → mastery 0
        if 'mastery_levels' not in student:
            student['mastery_levels'] = {}
        if student['mastery_levels'].get(topic, 0) == 0:
            student['mastery_levels'][topic] = max(0, 100 - severity * 10)

    student['updated_at'] = datetime.datetime.now().isoformat()
    store.write('students.json', data)
    flash('薄弱点已更新', 'success')
    return redirect(url_for('teacher.student_detail', student_id=student_id))


@teacher_bp.route('/student/<student_id>/weakness/delete', methods=['POST'])
@login_required
def delete_weakness(student_id):
    """Delete a weakness entry by topic."""
    store = get_store()
    data = store.read('students.json')
    student = None
    for s in data.get('students', []):
        if s['id'] == student_id:
            student = s
            break

    if not student:
        flash('学生未找到', 'error')
        return redirect(url_for('teacher.dashboard'))

    topic = request.form.get('topic', '')
    student['weaknesses'] = [w for w in student.get('weaknesses', []) if w['topic'] != topic]
    # Reset mastery level for this topic since weakness is removed
    if 'mastery_levels' in student:
        student['mastery_levels'][topic] = 0
    student['updated_at'] = datetime.datetime.now().isoformat()
    store.write('students.json', data)
    flash('薄弱点已删除', 'success')
    return redirect(url_for('teacher.student_detail', student_id=student_id))


@teacher_bp.route('/student/<student_id>/delete', methods=['POST'])
@login_required
def delete_student(student_id):
    store = get_store()
    data = store.read('students.json')
    data['students'] = [s for s in data.get('students', []) if s['id'] != student_id]
    store.write('students.json', data)
    flash('学生已删除', 'success')
    return redirect(url_for('teacher.dashboard'))


@teacher_bp.route('/problems')
@login_required
def problem_bank():
    store = get_store()
    problems_data = store.read('problem_bank.json')
    problems = problems_data.get('problems', [])

    topic_filter = request.args.get('topic', '')
    student_filter = request.args.get('student', '')

    if topic_filter:
        problems = [p for p in problems if p.get('topic') == topic_filter]
    if student_filter:
        problems = [p for p in problems if p.get('generated_for_student') == student_filter]

    # Get students for filter
    students_data = store.read('students.json')
    students = students_data.get('students', [])

    # Build student weakness map for auto-select
    student_weakness_topics = {}
    for s in students:
        student_weakness_topics[s['id']] = [w['topic'] for w in s.get('weaknesses', [])]

    return render_template('teacher_problem_bank.html',
                           problems=problems,
                           topics=MATH_TOPICS,
                           students=students,
                           current_topic=topic_filter,
                           current_student=student_filter,
                           student_weakness_topics=student_weakness_topics)


@teacher_bp.route('/problems/delete', methods=['POST'])
@login_required
def delete_problems():
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"success": False, "error": "未选择题目"}), 400
    store = get_store()
    pdata = store.read('problem_bank.json')
    before = len(pdata.get('problems', []))
    pdata['problems'] = [p for p in pdata.get('problems', []) if p['id'] not in ids]
    store.write('problem_bank.json', pdata)
    after = len(pdata.get('problems', []))
    return jsonify({"success": True, "deleted": before - after})


@teacher_bp.route('/export_problems', methods=['POST'])
@login_required
def export_problems():
    import json
    export_data = json.loads(request.form.get('export_data', '[]'))

    store = get_store()
    problems_data = store.read('problem_bank.json')
    all_problems = problems_data.get('problems', [])

    # Build a lookup of per-problem options
    opts_map = {}
    for item in export_data:
        opts_map[item['id']] = item

    selected = [p for p in all_problems if p['id'] in opts_map]
    topic_names = {t['id']: t['name'] for t in MATH_TOPICS}

    # Build HTML-based Word document (Office compatible)
    html_parts = ['''<html xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:w="urn:schemas-microsoft-com:office:word"
xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="UTF-8">
<style>
body { font-family: '微软雅黑', sans-serif; font-size: 14px; line-height: 1.8; }
h1 { text-align: center; font-size: 22px; }
h2 { font-size: 16px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
h3 { font-size: 14px; color: #555; }
.question { font-size: 15px; font-weight: bold; }
.answer { color: #10b981; font-weight: bold; }
ol, ul { margin-top: 4px; }
li { margin-bottom: 4px; }
</style></head><body>''']
    html_parts.append(f'<h1>八年级数学习题集</h1>')
    html_parts.append(f'<p style="text-align:center; color:#888;">共 {len(selected)} 道题目</p>')

    for i, p in enumerate(selected, 1):
        opts = opts_map.get(p['id'], {})
        topic_name = topic_names.get(p.get('topic', ''), p.get('topic', ''))
        html_parts.append(f'<h2>第{i}题 [{topic_name}] {"⭐" * (p.get("difficulty", 3))}</h2>')
        html_parts.append(f'<p class="question">{p.get("question", "")}</p>')

        if opts.get('include_answer') and p.get('answer'):
            html_parts.append(f'<p class="answer">答案：{p["answer"]}</p>')

        if opts.get('include_steps') and p.get('solution_steps'):
            html_parts.append('<h3>解题步骤</h3><ol>')
            for step in p['solution_steps']:
                html_parts.append(f'<li>{step}</li>')
            html_parts.append('</ol>')

        if opts.get('include_hints') and p.get('hints'):
            html_parts.append('<h3>提示</h3><ul>')
            for hint in p['hints']:
                html_parts.append(f'<li>{hint}</li>')
            html_parts.append('</ul>')

    html_parts.append('</body></html>')
    html_content = '\n'.join(html_parts)

    buf = io.BytesIO()
    buf.write(html_content.encode('utf-8'))
    buf.seek(0)

    return send_file(buf,
                     mimetype='application/msword',
                     as_attachment=True,
                     attachment_filename='八年级数学习题集.doc')


# ── Wrong Problem Collection ──

@teacher_bp.route('/wrong_problems')
@login_required
def wrong_problems():
    store = get_store()
    wp_data = store.read('wrong_problems.json')
    wrong_list = wp_data.get('wrong_problems', [])

    student_filter = request.args.get('student', '')
    if student_filter:
        wrong_list = [w for w in wrong_list if w.get('student_id') == student_filter]

    topic_filter = request.args.get('topic', '')
    if topic_filter:
        wrong_list = [w for w in wrong_list if w.get('topic') == topic_filter]

    students_data = store.read('students.json')
    students = students_data.get('students', [])

    wrong_list.sort(key=lambda w: w.get('created_at', ''), reverse=True)

    return render_template('teacher_wrong_problems.html',
                           wrong_problems=wrong_list,
                           students=students,
                           topics=MATH_TOPICS,
                           current_student=student_filter,
                           current_topic=topic_filter)


@teacher_bp.route('/wrong_problems/add', methods=['POST'])
@login_required
def add_wrong_problem():
    store = get_store()
    wp_data = store.read('wrong_problems.json')

    wp_id = store.generate_id('wrong_problems.json')
    wp_data = store.read('wrong_problems.json')

    new_wp = {
        "id": wp_id,
        "student_id": request.form.get('student_id', ''),
        "student_name": request.form.get('student_name', ''),
        "question": request.form.get('question', '').strip(),
        "answer": request.form.get('answer', '').strip(),
        "student_answer": request.form.get('student_answer', '').strip(),
        "topic": request.form.get('topic', ''),
        "difficulty": int(request.form.get('difficulty', 3)),
        "solution_steps": request.form.get('solution_steps', '').strip(),
        "hints": request.form.get('hints', '').strip(),
        "reason": request.form.get('reason', ''),
        "created_at": datetime.datetime.now().isoformat(),
    }
    wp_data['wrong_problems'].append(new_wp)
    store.write('wrong_problems.json', wp_data)
    flash('错题已添加', 'success')
    redirect_to = request.form.get('redirect_to', '')
    if redirect_to == 'student_detail':
        return redirect(url_for('teacher.student_detail', student_id=request.form.get('student_id', '')))
    return redirect(url_for('teacher.wrong_problems', student=request.form.get('student_id', '')))


@teacher_bp.route('/wrong_problems/<wp_id>/delete', methods=['POST'])
@login_required
def delete_wrong_problem(wp_id):
    store = get_store()
    wp_data = store.read('wrong_problems.json')
    wp_data['wrong_problems'] = [w for w in wp_data['wrong_problems'] if w['id'] != wp_id]
    store.write('wrong_problems.json', wp_data)
    flash('错题已删除', 'success')
    return redirect(url_for('teacher.wrong_problems'))


@teacher_bp.route('/wrong_problems/export', methods=['POST'])
@login_required
def export_wrong_problems():
    import json
    export_data = json.loads(request.form.get('export_data', '[]'))

    store = get_store()
    wp_data = store.read('wrong_problems.json')
    all_wp = wp_data.get('wrong_problems', [])

    opts_map = {item['id']: item for item in export_data}
    selected = [w for w in all_wp if w['id'] in opts_map]
    topic_names = {t['id']: t['name'] for t in MATH_TOPICS}

    html_parts = ['''<html xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:w="urn:schemas-microsoft-com:office:word"
xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="UTF-8">
<style>
body { font-family: '微软雅黑', sans-serif; font-size: 14px; line-height: 1.8; }
h1 { text-align: center; font-size: 22px; color: #dc2626; }
h2 { font-size: 16px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
h3 { font-size: 14px; color: #555; }
.question { font-size: 15px; font-weight: bold; }
.wrong-answer { color: #ef4444; font-weight: bold; }
.correct-answer { color: #10b981; font-weight: bold; }
ol, ul { margin-top: 4px; }
li { margin-bottom: 4px; }
</style></head><body>''']
    html_parts.append('<h1>📝 错题集</h1>')
    html_parts.append(f'<p style="text-align:center; color:#888;">共 {len(selected)} 道错题</p>')

    for i, w in enumerate(selected, 1):
        opts = opts_map.get(w['id'], {})
        topic_name = topic_names.get(w.get('topic', ''), w.get('topic', ''))
        html_parts.append(f'<h2>第{i}题 [{topic_name}]</h2>')
        html_parts.append(f'<p class="question">{w.get("question", "")}</p>')

        if w.get('student_answer'):
            html_parts.append(f'<p class="wrong-answer">❌ 学生作答：{w["student_answer"]}</p>')
        if opts.get('include_answer') and w.get('answer'):
            html_parts.append(f'<p class="correct-answer">✅ 正确答案：{w["answer"]}</p>')

        if opts.get('include_steps') and w.get('solution_steps'):
            html_parts.append('<h3>解题步骤</h3><ol>')
            for step in w['solution_steps'].split('\n'):
                step = step.strip()
                if step:
                    html_parts.append(f'<li>{step}</li>')
            html_parts.append('</ol>')

        if opts.get('include_hints') and w.get('hints'):
            html_parts.append('<h3>提示</h3><ul>')
            for hint in w['hints'].split('\n'):
                hint = hint.strip()
                if hint:
                    html_parts.append(f'<li>{hint}</li>')
            html_parts.append('</ul>')

        if w.get('reason'):
            html_parts.append(f'<p style="color:#888; font-size:12px;">错误原因：{w["reason"]}</p>')

    html_parts.append('</body></html>')
    html_content = '\n'.join(html_parts)

    buf = io.BytesIO()
    buf.write(html_content.encode('utf-8'))
    buf.seek(0)

    return send_file(buf,
                     mimetype='application/msword',
                     as_attachment=True,
                     attachment_filename='错题集.doc')
