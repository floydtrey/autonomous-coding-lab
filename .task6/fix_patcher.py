from pathlib import Path

path = Path('.task6/apply_task6.py')
text = path.read_text(encoding='utf-8')
old = '''replace_once(tda, "    def fake(_):\\n", "    def fake(_, __):\\n")
replace_once(tda, "    def fake(_):\\n", "    def fake(_, __):\\n")
'''
new = '''text = read(tda)
anchor = "    def fake(_):\\n"
if text.count(anchor) != 2:
    raise SystemExit(f"{tda}: expected two fake callback anchors, found {text.count(anchor)}")
write(tda, text.replace(anchor, "    def fake(_, __):\\n", 2))
'''
if text.count(old) != 1:
    raise SystemExit(f'patcher duplicate-anchor block count={text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
