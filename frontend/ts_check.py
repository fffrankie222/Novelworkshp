import os, re, sys

errors = []
src_dir = 'src'

ts_files = []
for root, dirs, files in os.walk(src_dir):
    for f in files:
        if f.endswith('.ts') or f.endswith('.tsx'):
            ts_files.append(os.path.join(root, f))

print(f'Found {len(ts_files)} TypeScript files')

for fpath in sorted(ts_files):
    with open(fpath) as f:
        content = f.read()

    pairs = [('{', '}'), ('[', ']'), ('(', ')')]
    for open_c, close_c in pairs:
        o = content.count(open_c)
        c = content.count(close_c)
        if o != c:
            errors.append(f'{fpath}: unbalanced {open_c}{close_c} ({o} vs {c})')

    pattern = r"from ['\"]([^'\"]+)['\"]"
    for match in re.finditer(pattern, content):
        imp = match.group(1)
        if imp.startswith('.'):
            base = os.path.dirname(fpath)
            target = os.path.normpath(os.path.join(base, imp))
            candidates = [
                target + '.ts', target + '.tsx',
                os.path.join(target, 'index.ts'),
                os.path.join(target, 'index.tsx'),
            ]
            found = any(os.path.exists(c) for c in candidates)
            if not found:
                errors.append(f'{fpath}: import not found: {imp}')

print(f'\n--- {len(errors)} issues ---')
for e in errors:
    print(e)
