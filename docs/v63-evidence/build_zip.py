"""Build/validate the RC ZIP exclusively from Git bytes, including both public caches."""
import argparse
from hashlib import sha256
from pathlib import Path
import json
import subprocess
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

BASE="aee41fb328027f8927a55d65c68e8a3e30332697"
OUT=Path(__file__).resolve().parent
ARCHIVE=Path("drafts/ten-locks-team3-v6.3-rc.zip")
CACHES={
    "tier09":"06c9a4fc5a30c893a9bd1e4e0b862070c2b2a17545a9d10e5465fa6dc7f1083b",
    "tier10":"b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6",
}


def git(*args):
    return subprocess.check_output(["git",*args])


def build(ref):
    paths=git("ls-tree","-r","--name-only",ref,"submissions/team3").decode().splitlines()
    excluded={"tier01/test_solution.py","tier01/validate_quantum.py"}
    members={}
    for path in paths:
        local=path.removeprefix("submissions/team3/")
        if local in excluded:
            continue
        allowed={"README.md","WRITEUP.md",*(f"{t}/public_operations.json" for t in CACHES)}
        assert local.endswith(".py") or local in allowed,local
        members["team3/"+local]=git("show",ref+":"+path)
    for tier,expected in CACHES.items():
        member=f"team3/{tier}/public_operations.json"
        assert sha256(members[member]).hexdigest()==expected
        assert members[member]==git("show",BASE+":submissions/"+member)
    assert all(f"team3/tier{n:02}/solution.py" in members for n in range(1,11))
    assert {"team3/README.md","team3/WRITEUP.md"}.issubset(members)
    with ZipFile(ARCHIVE,"w") as z:
        for name,data in sorted(members.items()):
            info=ZipInfo(name)
            info.create_system=3
            info.external_attr=0o100644<<16
            z.writestr(info,data,compress_type=ZIP_DEFLATED,compresslevel=9)
    with ZipFile(ARCHIVE) as z:
        assert z.testzip() is None and z.namelist()==sorted(members)
        assert all(z.read(name)==data for name,data in members.items())
    manifest=dict(team_tree=git("rev-parse",ref+":submissions/team3").decode().strip(),
                  zip_sha256=sha256(ARCHIVE.read_bytes()).hexdigest(),
                  contents={k:sha256(v).hexdigest() for k,v in sorted(members.items())})
    (OUT/"zip-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("ref")
    build(p.parse_args().ref)
