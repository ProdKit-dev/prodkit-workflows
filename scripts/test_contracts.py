#!/usr/bin/env python3
import json, pathlib, tempfile, subprocess, shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]

def main():
    # Self manifest validates current version.
    subprocess.run(['python3',str(ROOT/'scripts/validate_release_manifest.py'),(ROOT/'VERSION').read_text().strip(),'--root',str(ROOT)],check=True)
    # Bootstrap must materialize immutable refs and all adapters.
    with tempfile.TemporaryDirectory() as td:
        dest=pathlib.Path(td)/'consumer'; dest.mkdir()
        sha='a'*40
        subprocess.run(['python3',str(ROOT/'scripts/bootstrap_consumer.py'),'--workflows-repository','example/workflows','--workflows-sha',sha,'--destination',str(dest)],check=True)
        for name in ['ci.yml','security.yml','release.yml']:
            text=(dest/'.github/workflows'/name).read_text()
            if f'example/workflows/.github/workflows/' not in text or f'@{sha}' not in text: raise SystemExit('bootstrap pin failure')
        if not (dest/'.prodkit/release.json').is_file(): raise SystemExit('bootstrap manifest missing')
        if len(list((dest/'.prodkit/workflows').glob('*.sh'))) < 10: raise SystemExit('bootstrap adapters incomplete')
    print('contract tests passed')
if __name__=='__main__': main()
