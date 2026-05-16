import json
import os
import threading

class JsonStore:
    """Thread-safe JSON file read/write with file locking."""

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self._locks = {}

    def _get_lock(self, filename):
        if filename not in self._locks:
            self._locks[filename] = threading.Lock()
        return self._locks[filename]

    def _path(self, filename):
        return os.path.join(self.base_dir, filename)

    def read(self, filename):
        path = self._path(filename)
        if not os.path.exists(path):
            return None
        with self._get_lock(filename):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

    def write(self, filename, data):
        path = self._path(filename)
        with self._get_lock(filename):
            tmp_path = path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)

    def generate_id(self, filename):
        data = self.read(filename)
        if data is None:
            return None
        data['id_counter'] = data.get('id_counter', 0) + 1
        new_id = f"{filename.replace('.json','')}_{data['id_counter']:04d}"
        self.write(filename, data)
        return new_id


_store = None

def get_store():
    global _store
    if _store is None:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'storage')
        _store = JsonStore(base_dir)
    return _store
