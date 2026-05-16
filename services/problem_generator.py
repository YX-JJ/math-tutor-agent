from storage.json_store import get_store
from services.prompt_builder import get_builder
from services.deepseek_client import get_client
from config import get_config
import datetime


class ProblemGenerator:
    def __init__(self):
        self.store = get_store()
        self.builder = get_builder()
        self.client = get_client()
        self.cfg = get_config()

    def generate_problem(self, student, topic_id, difficulty=3):
        messages = self.builder.build_problem_gen_prompt(student, topic_id, difficulty)
        result = self.client.chat_with_retry(
            messages,
            temperature=self.cfg.get('temperature_problem_gen', 0.9),
            max_tokens=self.cfg.get('max_tokens', 2048)
        )

        content = result.get('content', '')
        problem_data = self.client.parse_json_response(content)

        if not problem_data:
            # Try a second time with a stronger system prompt
            messages[0]['content'] = '你必须只返回JSON格式，不要包含任何其他文字、markdown标记或解释。直接返回JSON对象。'
            result2 = self.client.chat_with_retry(
                messages,
                temperature=0.3,
                max_tokens=self.cfg.get('max_tokens', 2048)
            )
            problem_data = self.client.parse_json_response(result2.get('content', ''))

        if not problem_data:
            return None

        # Normalize fields
        if 'question' not in problem_data:
            # Try alternative field names
            for key in problem_data:
                if 'question' in key.lower() or 'problem' in key.lower():
                    problem_data['question'] = problem_data[key]
                    break
            if 'question' not in problem_data:
                return None

        # Ensure required fields exist
        problem_data.setdefault('answer', problem_data.get('correct_answer', ''))
        problem_data.setdefault('solution_steps', [])
        problem_data.setdefault('hints', [problem_data.get('hint', '')] if problem_data.get('hint') else [])
        problem_data.setdefault('difficulty', difficulty)
        problem_data.setdefault('topic', topic_id)
        problem_data.setdefault('subtopic', '')

        # Save to problem bank
        data = self.store.read('problem_bank.json')
        problem_id = self.store.generate_id('problem_bank.json')
        data = self.store.read('problem_bank.json')

        problem_data['id'] = problem_id
        problem_data['created_by'] = 'ai'
        problem_data['generated_for_student'] = student['id']
        problem_data['created_at'] = datetime.datetime.now().isoformat()
        problem_data['times_assigned'] = 0
        problem_data['success_rate'] = 0
        problem_data['student_attempted'] = False
        problem_data['student_correct'] = False

        data['problems'].append(problem_data)
        self.store.write('problem_bank.json', data)
        return problem_data

    def generate_multiple(self, student, topic_id, count=3, difficulty=3):
        results = []
        for _ in range(count):
            problem = self.generate_problem(student, topic_id, difficulty)
            if problem:
                results.append(problem)
        return results


_generator = None

def get_generator():
    global _generator
    if _generator is None:
        _generator = ProblemGenerator()
    return _generator
