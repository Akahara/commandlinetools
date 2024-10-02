import pathlib
import hashlib
import itertools

TYPE_DIRECTORY = 'D'
TYPE_FILE = 'F'

class StateFile:
    def __init__(self, path, is_directory, file_hash=None):
        self.path = path
        self.is_directory = is_directory
        self.file_hash = file_hash

    def __str__(self) -> str:
        return f"{TYPE_DIRECTORY if self.is_directory else TYPE_FILE},{self.path},{self.file_hash}"
    def __repr__(self) -> str:
        return f"({TYPE_DIRECTORY if self.is_directory else TYPE_FILE},{self.path},{'*' if self.file_hash is None else self.file_hash[:4]})"
    def __lt__(self, other):
        return self.is_directory and not other.is_directory or self.path < other.path 

    @staticmethod
    def parse(line):
        parts = line.split(',')
        if parts[0] == TYPE_DIRECTORY:
            return StateFile(parts[1], True)
        else:
            return StateFile(parts[1], False, parts[2])


def read_local_files(path):
    all_files = list(pathlib.Path(path).rglob('*'))
    state = []
    for f in all_files:
        if f.is_dir():
            state.append(StateFile(str(f.relative_to(path)), True))
        elif f.is_file():
            state.append(StateFile(str(f.relative_to(path)), False, hash_file(f)))
    return state

def hash_file(path):
    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()

def parse_state(state_content):
    return [StateFile.parse(line) for line in state_content.splitlines()]

def serialize_state(state):
    return '\n'.join(str(s) for s in state)

def diff_states(state_from, state_to):
    diff = (new, removed, changed) = ([], [], [])
    
    state_from = [] if state_from is None else state_from
    state_to = [] if state_to is None else state_to

    from_map = {f.path: f for f in state_from}
    to_map = {f.path: f for f in state_to}
    for to_file in state_to:
        if to_file.path not in from_map:
            new.append(to_file)
            continue
        from_file = from_map[to_file.path]
        if from_file.file_hash != to_file.file_hash:
            changed.append(to_file)
    for from_file in state_from:
        if from_file.path not in to_map:
            removed.append(from_file)

    return diff

def remove_ignored(state, excluded, excluded_paths=None):
    state.sort()
    excluded_paths = [] if excluded_paths is None else excluded_paths
    included_files = []

    for f in state:
        pure_path = pathlib.PurePath(f.path)
        parent_path = str(pathlib.Path(f.path).parent)
        if parent_path in excluded_paths or any(pure_path.match(ex) for ex in excluded):
            excluded_paths.append(f.path)
        else:
            included_files.append(f)

    return included_files

def merge_diff(state, applied_diff):
    (new, removed, changed) = applied_diff
    new_state_map = {f.path: f for f in state}
    for f in removed:
        del new_state_map[f.path]
    for changed in itertools.chain(new, changed):
        new_state_map[changed.path] = changed
    return list(new_state_map.values())
