import os
from pathlib import Path

# Borrar inspect_git temporal más tarde
repo_root = Path('.')

def list_all_files():
    files = []
    for p in repo_root.rglob('*'):
        if p.is_file():
            parts = p.parts
            if any(part in ['.git', '.venv', '__pycache__', '.pytest_cache'] for part in parts):
                continue
            files.append(str(p.as_posix()))
    return sorted(files)

working_files = list_all_files()

# Leer tree de HEAD
import zlib
def read_object(sha):
    p = Path(f'.git/objects/{sha[:2]}/{sha[2:]}')
    if not p.exists():
        return None, None
    raw = zlib.decompress(p.read_bytes())
    null_idx = raw.find(b'\x00')
    header = raw[:null_idx].decode('latin1')
    body = raw[null_idx+1:]
    obj_type, size = header.split(' ')
    return obj_type, body

def get_tree_files(tree_sha, prefix=""):
    files = {}
    _, body = read_object(tree_sha)
    if not body:
        return files
    idx = 0
    while idx < len(body):
        space_idx = body.find(b' ', idx)
        if space_idx == -1:
            break
        mode = body[idx:space_idx].decode('latin1')
        null_idx = body.find(b'\x00', space_idx)
        name = body[space_idx+1:null_idx].decode('utf-8', errors='replace')
        sha = body[null_idx+1:null_idx+21].hex()
        path = f"{prefix}{name}"
        if mode == '40000': # dir
            sub = get_tree_files(sha, prefix=f"{path}/")
            files.update(sub)
        else:
            files[path] = sha
        idx = null_idx + 21
    return files

# Tree de 7119232
head_tree = "74dfcc60fab4c3ecf0aac5a1b6eb6ffb859a5162"
committed_files = get_tree_files(head_tree)

out = []
out.append("=== ARCHIVOS EN EL COMMIT QUE ACABAS DE HACER (7119232) ===")
for f in sorted(committed_files.keys()):
    out.append(f"  - {f}")

out.append("\n=== ARCHIVOS PENDIENTES EN EL SEGUNDO COMMIT (LOS QUE QUEDAN POR SUBIR) ===")
for f in working_files:
    if f in ["inspect_git.py", "git_report.txt"]:
        continue
    if f not in committed_files:
        out.append(f"  + NUEVO (No estaba en el commit anterior): {f}")
    else:
        # Check if modified
        content = Path(f).read_bytes()
        # compute git blob sha
        import hashlib
        header = f"blob {len(content)}\x00".encode('latin1')
        blob_sha = hashlib.sha1(header + content).hexdigest()
        if blob_sha != committed_files[f]:
            out.append(f"  ~ MODIFICADO (Cambió después del commit anterior): {f}")

Path('git_report.txt').write_text('\n'.join(out), encoding='utf-8')
