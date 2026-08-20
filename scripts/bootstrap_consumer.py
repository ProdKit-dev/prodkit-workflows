#!/usr/bin/env python3
import argparse, pathlib, re, shutil, stat

def main():
    ap=argparse.ArgumentParser(description='Install thin immutable prodkit-workflows consumer contracts.')
    ap.add_argument('--workflows-repository',default='ProdKit-dev/prodkit-workflows')
    ap.add_argument('--workflows-sha',required=True)
    ap.add_argument('--destination',required=True)
    ap.add_argument('--force',action='store_true')
    a=ap.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}',a.workflows_sha): raise SystemExit('--workflows-sha must be a full lowercase 40-character SHA')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.workflows_repository): raise SystemExit('invalid workflows repository')
    src=pathlib.Path(__file__).resolve().parents[1]/'templates'; dest=pathlib.Path(a.destination).resolve()
    mapping={
      src/'caller/ci.yml':dest/'.github/workflows/ci.yml', src/'caller/security.yml':dest/'.github/workflows/security.yml', src/'caller/release.yml':dest/'.github/workflows/release.yml',
      src/'consumer/.prodkit/release.json':dest/'.prodkit/release.json'}
    for s in (src/'consumer/.prodkit/workflows').iterdir(): mapping[s]=dest/'.prodkit/workflows'/s.name
    for s,t in mapping.items():
        if t.exists() and not a.force: print(f'skip existing {t}'); continue
        t.parent.mkdir(parents=True,exist_ok=True)
        text=s.read_text().replace('WORKFLOWS_REPOSITORY',a.workflows_repository).replace('REPLACE_WITH_PRODKIT_WORKFLOWS_SHA',a.workflows_sha)
        t.write_text(text,newline='\n')
        if t.suffix=='.sh': t.chmod(t.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f'wrote {t}')
if __name__=='__main__': main()
