from datetime import datetime
from storage.json_store import get_store


class ConversationManager:
    def __init__(self):
        self.store = get_store()

    def get_recent_messages(self, student_id, limit=20):
        """Get recent messages for a student across all sessions."""
        data = self.store.read('conversations.json')
        if not data:
            return []

        all_messages = []
        for conv in data.get('conversations', []):
            if conv.get('student_id') == student_id:
                for msg in conv.get('messages', []):
                    if msg['role'] != 'system':
                        all_messages.append({
                            'role': msg['role'],
                            'content': msg['content'],
                        })

        # Return last N messages
        return all_messages[-limit:] if len(all_messages) > limit else all_messages

    def start_session(self, student_id, topic_focus="", problem_id=""):
        """Start a new conversation session."""
        data = self.store.read('conversations.json')
        session_id = self.store.generate_id('conversations.json')
        data = self.store.read('conversations.json')

        session = {
            "id": session_id,
            "student_id": student_id,
            "session_start": datetime.now().isoformat(),
            "session_end": None,
            "topic_focus": topic_focus,
            "problem_id": problem_id,
            "messages": [],
        }
        data['conversations'].append(session)
        self.store.write('conversations.json', data)
        return session_id

    def save_message(self, session_id, role, content, metadata=None):
        """Save a message to a session."""
        data = self.store.read('conversations.json')
        for conv in data.get('conversations', []):
            if conv['id'] == session_id:
                msg = {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                }
                if metadata:
                    msg["metadata"] = metadata
                conv['messages'].append(msg)
                self.store.write('conversations.json', data)
                return

    def end_session(self, session_id):
        """Mark a session as ended."""
        data = self.store.read('conversations.json')
        for conv in data.get('conversations', []):
            if conv['id'] == session_id:
                conv['session_end'] = datetime.now().isoformat()
                self.store.write('conversations.json', data)
                return

    def get_sessions(self, student_id):
        """Get all session summaries for a student."""
        data = self.store.read('conversations.json')
        sessions = []
        for conv in data.get('conversations', []):
            if conv.get('student_id') == student_id:
                sessions.append({
                    'id': conv['id'],
                    'session_start': conv.get('session_start'),
                    'session_end': conv.get('session_end'),
                    'topic_focus': conv.get('topic_focus', ''),
                    'message_count': len(conv.get('messages', [])),
                })
        return sorted(sessions, key=lambda s: s['session_start'], reverse=True)

    def get_session(self, session_id):
        """Get a full session by ID."""
        data = self.store.read('conversations.json')
        for conv in data.get('conversations', []):
            if conv['id'] == session_id:
                return conv
        return None

    def get_session_text(self, session_id):
        """Get conversation as formatted text for analysis."""
        session = self.get_session(session_id)
        if not session:
            return ""
        lines = []
        for msg in session.get('messages', []):
            if msg['role'] == 'user':
                lines.append(f"学生：{msg['content']}")
            elif msg['role'] == 'assistant':
                lines.append(f"AI老师：{msg['content']}")
        return '\n\n'.join(lines)


_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = ConversationManager()
    return _manager
