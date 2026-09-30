"""Fetch and verify model files. Run this on a machine WITH internet access.

    python -m faceswap.download [--models-dir DIR] [--skip-enhancer]

Then copy the models directory to the airgapped PC (or point
FACESWAP_MODELS_DIR at it). Existing files with a valid checksum are skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .models import MODELS, ModelFile, default_models_dir


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch(url: str, dest: Path) -> None:
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "faceswap-downloader"})
    with urllib.request.urlopen(req) as resp, dest.open("wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while chunk := resp.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / total:6.1%} of {total / 1e6:.0f} MB", end="", flush=True)
        print()


def ensure_model(model: ModelFile, models_dir: Path, archive_cache: dict[str, Path], tmp: Path) -> bool:
    dest = models_dir / model.filename
    if dest.is_file() and sha256_of(dest) in model.checksums:
        print(f"[ok]   {model.filename} already present")
        return True

    for url, sha in model.sources:
        try:
            if model.zip_member:
                archive = archive_cache.get(url)
                if archive is None:
                    archive = tmp / Path(url).name
                    _fetch(url, archive)
                    archive_cache[url] = archive
                staged = tmp / model.filename
                with zipfile.ZipFile(archive) as zf:
                    member = next(n for n in zf.namelist() if n.endswith(model.zip_member))
                    with zf.open(member) as src, staged.open("wb") as out:
                        shutil.copyfileobj(src, out)
            else:
                staged = tmp / model.filename
                _fetch(url, staged)

            actual = sha256_of(staged)
            if actual != sha:
                print(f"[warn] checksum mismatch for {model.filename} from {url}: {actual}")
                continue
            shutil.move(str(staged), dest)
            print(f"[ok]   {model.filename} verified")
            return True
        except Exception as exc:  # try the next mirror
            print(f"[warn] {url} failed: {exc}")
    print(f"[fail] could not obtain {model.filename}")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models-dir", type=Path, default=default_models_dir())
    parser.add_argument("--skip-enhancer", action="store_true", help="don't fetch the optional GFPGAN model")
    parser.add_argument("--verify", action="store_true", help="only verify files already on disk")
    args = parser.parse_args(argv)

    models_dir: Path = args.models_dir.expanduser().resolve()
    models_dir.mkdir(parents=True, exist_ok=True)
    print(f"models directory: {models_dir}")

    wanted = [m for m in MODELS.values() if m.required or not args.skip_enhancer]
    ok = True
    if args.verify:
        for m in wanted:
            p = models_dir / m.filename
            good = p.is_file() and sha256_of(p) in m.checksums
            print(f"[{'ok' if good else 'bad'}]   {m.filename}")
            ok &= good or not m.required
        return 0 if ok else 1

    with tempfile.TemporaryDirectory(dir=models_dir) as tmp:
        cache: dict[str, Path] = {}
        for m in wanted:
            ok &= ensure_model(m, models_dir, cache, Path(tmp)) or not m.required
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
