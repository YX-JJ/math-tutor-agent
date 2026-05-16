import os
from config import MATH_TOPICS, STORAGE_DIR


class PromptBuilder:
    def __init__(self):
        self._tutor_template = None
        self._problem_gen_template = None
        self._weakness_analyze_template = None
        self._topic_map = {t['id']: t['name'] for t in MATH_TOPICS}

    def _load_template(self, filename):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @property
    def tutor_template(self):
        # Always reload to pick up prompt changes (inexpensive)
        return self._load_template('system_tutor.txt')

    @property
    def problem_gen_template(self):
        if self._problem_gen_template is None:
            self._problem_gen_template = self._load_template('system_problem_gen.txt')
        return self._problem_gen_template

    @property
    def weakness_analyze_template(self):
        if self._weakness_analyze_template is None:
            self._weakness_analyze_template = self._load_template('system_weakness_analyze.txt')
        return self._weakness_analyze_template

    def _format_weaknesses(self, weaknesses):
        if not weaknesses:
            return "暂无记录"
        lines = []
        for w in weaknesses:
            topic_name = self._topic_map.get(w['topic'], w['topic'])
            sub = w.get('subtopic', '')
            severity = w.get('severity', 5)
            lines.append(f"  - {topic_name}" + (f"（{sub}）" if sub else "") + f"，严重程度: {severity}/10")
        return '\n'.join(lines) if lines else "暂无记录"

    def _format_strengths(self, strengths):
        if not strengths:
            return "暂无记录"
        lines = []
        for s in strengths:
            topic_name = self._topic_map.get(s['topic'], s['topic'])
            confidence = s.get('confidence', 5)
            lines.append(f"  - {topic_name}，自信度: {confidence}/10")
        return '\n'.join(lines) if lines else "暂无记录"

    def build_tutor_system_prompt(self, student):
        """Build the full system prompt for tutoring, injecting student profile data."""
        notes = student.get('teacher_notes', '').strip()
        return self.tutor_template.format(
            student_name=student.get('name', '同学'),
            learning_style=student.get('profile', {}).get('learning_style', '未设置'),
            weaknesses_list=self._format_weaknesses(student.get('weaknesses', [])),
            strengths_list=self._format_strengths(student.get('strengths', [])),
            accuracy=int((student.get('overall_accuracy', 0) or 0) * 100),
            teacher_notes=notes if notes else '无',
        )

    def build_chat_messages(self, student, history_messages, new_message):
        """Build the full message list for a chat completion request."""
        system_prompt = self.build_tutor_system_prompt(student)
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (already in OpenAI format with role/content)
        if history_messages:
            for msg in history_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": new_message})
        return messages

    def build_problem_gen_prompt(self, student, topic_id, difficulty, problem_type="自适应"):
        """Build messages for problem generation."""
        topic_name = self._topic_map.get(topic_id, topic_id)

        # Find student's weakness for this topic
        severity = 5
        subtopic = ""
        for w in student.get('weaknesses', []):
            if w['topic'] == topic_id:
                severity = w.get('severity', 5)
                subtopic = w.get('subtopic', '')
                break

        user_prompt = self.problem_gen_template.format(
            topic_name=topic_name,
            topic_id=topic_id,
            subtopic=subtopic or topic_name,
            difficulty=difficulty,
            problem_type=problem_type,
            severity=severity,
        )

        messages = [
            {"role": "system", "content": "你是一位资深的八年级数学题库设计专家。请严格按照JSON格式返回结果。"},
            {"role": "user", "content": user_prompt},
        ]
        return messages

    def build_weakness_analysis_prompt(self, student, conversation_text):
        """Build messages for weakness analysis."""
        current_weaknesses = self._format_weaknesses(student.get('weaknesses', []))
        user_prompt = self.weakness_analyze_template.format(
            conversation_text=conversation_text,
            current_weaknesses=current_weaknesses,
        )
        messages = [
            {"role": "system", "content": "你是一位数学教育评估专家。请严格按照JSON格式返回分析结果。"},
            {"role": "user", "content": user_prompt},
        ]
        return messages


_builder = None

def get_builder():
    global _builder
    if _builder is None:
        _builder = PromptBuilder()
    return _builder
