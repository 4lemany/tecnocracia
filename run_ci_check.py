import subprocess
import sys

out = []

out.append("=== RUFF CHECK ===")
try:
    p = subprocess.run([sys.executable, "-m", "ruff", "check", ".", "--ignore", "E501"], capture_output=True, text=True)
    out.append(f"Exit code: {p.returncode}")
    out.append("STDOUT:\n" + p.stdout)
    out.append("STDERR:\n" + p.stderr)
except Exception as e:
    out.append(f"Ruff error: {e}")

out.append("\n=== PYTEST TESTS ===")
try:
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], capture_output=True, text=True)
    out.append(f"Exit code: {p.returncode}")
    out.append("STDOUT:\n" + p.stdout)
    out.append("STDERR:\n" + p.stderr)
except Exception as e:
    out.append(f"Pytest error: {e}")

with open("ci_debug.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
