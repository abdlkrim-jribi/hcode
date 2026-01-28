import pathlib, importlib.util, sys

root = pathlib.Path(r'D:/workshops/Hcaude')
bad_files = []
for path in root.rglob('test_*.py'):
    # Skip virtual‑environment files
    if '.venv' in str(path):
        continue
    try:
        spec = importlib.util.spec_from_file_location('mod', str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        bad_files.append(str(path))

# Output one path per line (empty output means no problems)
print('\n'.join(bad_files))
