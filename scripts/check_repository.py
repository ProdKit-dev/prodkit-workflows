#!/usr/bin/env python3
import argparse, json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]

def check(security_only=False):
    errors=[]
    # JSON integrity
    for p in ROOT.rglob('*.json'):
        try: json.loads(p.read_text())
        except Exception as e: errors.append(f'{p.relative_to(ROOT)}: invalid JSON: {e}')
    # text hygiene and accidental credentials
    secret_patterns=[re.compile(r'ghp_[A-Za-z0-9]{30,}'),re.compile(r'github_pat_[A-Za-z0-9_]{30,}'),re.compile(r'AKIA[0-9A-Z]{16}')]
    for p in ROOT.rglob('*'):
        if not p.is_file() or '.git' in p.parts: continue
        try: text=p.read_text()
        except UnicodeDecodeError: continue
        if '\r\n' in text: errors.append(f'{p.relative_to(ROOT)}: CRLF')
        for i,line in enumerate(text.splitlines(),1):
            if line.rstrip()!=line: errors.append(f'{p.relative_to(ROOT)}:{i}: trailing whitespace')
        for pat in secret_patterns:
            if pat.search(text): errors.append(f'{p.relative_to(ROOT)}: possible credential')
    if not security_only:
        expected=['.github/workflows/reusable-ci.yml','.github/workflows/reusable-security.yml','.github/workflows/reusable-release.yml','contracts/release-manifest.schema.json','rulesets/org-main.json','rulesets/org-release-tags.json']
        for x in expected:
            if not (ROOT/x).is_file(): errors.append(f'missing {x}')
        # All production third-party action refs must be full SHA. Local uses are allowed. Templates intentionally contain a replacement sentinel.
        for p in (ROOT/'.github/workflows').glob('*.yml'):
            for i,line in enumerate(p.read_text().splitlines(),1):
                m=re.search(r'\buses:\s*([^\s#]+)',line)
                if not m: continue
                ref=m.group(1)
                if ref.startswith('./'): continue
                if '@' not in ref or not re.fullmatch(r'.+@[0-9a-f]{40}',ref): errors.append(f'{p.relative_to(ROOT)}:{i}: action/workflow not full-SHA pinned: {ref}')
        version=(ROOT/'VERSION').read_text().strip()
        if f'## [{version}]' not in (ROOT/'CHANGELOG.md').read_text(): errors.append('CHANGELOG missing current version')
        if not (ROOT/f'docs/V{version}.md').is_file(): errors.append('version release notes missing')
    return errors

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--security-only',action='store_true'); a=ap.parse_args(); errors=check(a.security_only)
    if errors:
        print('\n'.join('ERROR: '+e for e in errors),file=sys.stderr); raise SystemExit(1)
    print('repository checks passed')
if __name__=='__main__': main()
