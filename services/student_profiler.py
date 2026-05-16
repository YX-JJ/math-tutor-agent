from storage.json_store import get_store
from services.conversation_manager import get_manager
from services.prompt_builder import get_builder
from services.deepseek_client import get_client
import datetime


class StudentProfiler:
    def __init__(self):
        self.store = get_store()
        self.manager = get_manager()
        self.builder = get_builder()
        self.client = get_client()

    def _get_student(self, student_id):
        data = self.store.read('students.json')
        for s in data.get('students', []):
            if s['id'] == student_id:
                return s, data
        return None, None

    def _build_conversation_text(self, sessions, analyzed_map, include_all):
        """Build conversation text for analysis.

        Returns (all_text, new_text, snapshot, has_new).
        - all_text: ALL messages from all sessions (for wrong problem detection)
        - new_text: only unanalyzed messages (for incremental mastery updates)
        - snapshot: {session_id: current_message_count}
        - has_new: True if there are any unanalyzed messages
        """
        all_parts = []
        new_parts = []
        snapshot = {}
        has_new = False

        for sess in sessions:
            full = self.manager.get_session(sess['id'])
            if not full:
                continue
            msgs = [m for m in full.get('messages', []) if m['role'] != 'system']
            current_count = len(msgs)
            if current_count == 0:
                continue

            analyzed_count = analyzed_map.get(sess['id'], 0) if isinstance(analyzed_map, dict) else 0
            snapshot[sess['id']] = current_count

            # Always collect all messages for wrong problem detection
            all_lines = []
            for m in msgs:
                role = '学生' if m['role'] == 'user' else 'AI老师'
                all_lines.append(f"{role}：{m['content']}")
            if all_lines:
                all_parts.append("【会话】\n" + '\n\n'.join(all_lines))

            # Collect new messages for incremental mastery updates
            if current_count > analyzed_count:
                has_new = True
                new_msgs = msgs[analyzed_count:]
                new_lines = []
                for m in new_msgs:
                    role = '学生' if m['role'] == 'user' else 'AI老师'
                    new_lines.append(f"{role}：{m['content']}")
                if new_lines:
                    new_parts.append("【会话】\n" + '\n\n'.join(new_lines))

        all_text = '\n\n'.join(all_parts) if all_parts else ''
        new_text = '\n\n'.join(new_parts) if new_parts else ''
        return all_text, new_text, snapshot, has_new

    def analyze_student(self, student_id):
        """Analyze student's conversations. Always scans ALL messages for wrong problems,
        but only uses new messages for incremental mastery/weakness updates."""
        student, _ = self._get_student(student_id)
        if not student:
            return {"error": "学生未找到"}

        sessions = self.manager.get_sessions(student_id)
        if not sessions:
            return {"error": "该学生暂无对话记录"}

        analyzed_map = student.get('analyzed_sessions', {})
        all_text, new_text, snapshot, has_new = self._build_conversation_text(
            sessions, analyzed_map, include_all=True
        )

        if not all_text:
            return {"error": "没有对话内容需要分析"}

        # Use all_text for AI analysis (so wrong problems from all conversations are detected)
        # If there are new messages, also include them for mastery updates
        conversation_text = all_text

        messages = self.builder.build_weakness_analysis_prompt(student, conversation_text)
        # Use higher max_tokens since we're sending all messages
        msg_count = len(conversation_text)
        max_tok = 2500 if msg_count > 3000 else 1500
        result = self.client.chat_with_retry(messages, temperature=0.5, max_tokens=max_tok)
        analysis = self.client.parse_json_response(result['content'])

        return {
            "conversation_text": conversation_text[:3000],
            "new_text": new_text,
            "analysis": analysis,
            "session_snapshot": snapshot,
            "has_new": has_new,
            "raw_response": result['content'][:500] if not analysis else None,
        }

    def analyze_and_update(self, student_id):
        """Analyze and update student profile. Always collects wrong problems from ALL
        conversations. Only updates problem counts from unanalyzed messages."""
        analysis_result = self.analyze_student(student_id)

        if 'error' in analysis_result:
            return analysis_result

        analysis = analysis_result.get('analysis')
        if not analysis:
            return {"success": False, "error": "AI分析结果解析失败"}

        student, data = self._get_student(student_id)
        if not student:
            return {"error": "学生未找到"}

        has_new = analysis_result.get('has_new', False)
        new_text = analysis_result.get('new_text', '')

        # Apply weakness updates — only UPDATE existing weaknesses, never add new ones.
        # Teacher controls which topics are weaknesses; AI only adjusts severity/evidence.
        updates = analysis.get('weakness_updates', [])
        if has_new:
            for update in updates:
                topic = update.get('topic', '')
                existing = None
                for w in student.get('weaknesses', []):
                    if w['topic'] == topic:
                        existing = w
                        break
                if existing:
                    severity_change = update.get('severity_change', 0)
                    existing['severity'] = max(1, min(10, existing.get('severity', 5) + severity_change))
                    existing['subtopic'] = update.get('subtopic', existing.get('subtopic', ''))
                    existing['evidence'] = update.get('evidence', existing.get('evidence', ''))
                    existing['last_assessed'] = datetime.date.today().isoformat()
                # Deleted/non-existing weaknesses are intentionally skipped — teacher manages the list

        # Apply mastery estimates — only for topics currently tracked as weaknesses
        new_mastery = {}
        if has_new:
            weak_topics = {w['topic'] for w in student.get('weaknesses', [])}
            new_mastery = analysis.get('new_mastery_estimates', {})
            for topic, level in new_mastery.items():
                if topic in weak_topics and topic in student.get('mastery_levels', {}):
                    student['mastery_levels'][topic] = max(0, min(100, int(level)))

        # Note: Problem counts (total_problems_attempted, overall_accuracy) are now
        # calculated in real-time from problem_bank.json during chat, not from AI analysis.

        # Auto-collect wrong problems — ALWAYS scan all messages (backup detection)
        wrong_problems = analysis.get('wrong_problems', [])
        wrong_count = 0
        if wrong_problems:
            wp_data = self.store.read('wrong_problems.json')
            existing_wp = wp_data.get('wrong_problems', [])
            existing_keys = set()
            for ew in existing_wp:
                key = (ew.get('student_id', ''), ew.get('question', '').strip())
                existing_keys.add(key)
            for wp in wrong_problems:
                q = wp.get('question', '').strip()
                if not q:
                    continue
                if (student_id, q) in existing_keys:
                    continue
                wp_id = self.store.generate_id('wrong_problems.json')
                wp_data = self.store.read('wrong_problems.json')
                new_wp = {
                    "id": wp_id,
                    "student_id": student_id,
                    "student_name": student.get('name', ''),
                    "question": q,
                    "answer": wp.get('answer', '').strip(),
                    "student_answer": wp.get('student_answer', '').strip(),
                    "topic": wp.get('topic', ''),
                    "difficulty": int(wp.get('difficulty', 3)),
                    "solution_steps": wp.get('solution_steps', '').strip(),
                    "hints": wp.get('hints', '').strip(),
                    "reason": wp.get('reason', ''),
                    "created_at": datetime.datetime.now().isoformat(),
                }
                wp_data['wrong_problems'].append(new_wp)
                self.store.write('wrong_problems.json', wp_data)
                existing_keys.add((student_id, q))
                wrong_count += 1

        # Update analyzed message counts per session
        existing_map = student.get('analyzed_sessions', {})
        if not isinstance(existing_map, dict):
            existing_map = {}
        snapshot = analysis_result.get('session_snapshot', {})
        for sid, count in snapshot.items():
            existing_map[sid] = count
        student['analyzed_sessions'] = existing_map

        student['updated_at'] = datetime.datetime.now().isoformat()
        self.store.write('students.json', data)

        return {
            "success": True,
            "summary": analysis.get('summary', '分析完成'),
            "updates_applied": len(updates),
            "new_mastery_levels": new_mastery,
            "wrong_problems_collected": wrong_count,
        }


_profiler = None

def get_profiler():
    global _profiler
    if _profiler is None:
        _profiler = StudentProfiler()
    return _profiler
