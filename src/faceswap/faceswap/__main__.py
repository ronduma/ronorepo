"""Entry point: `python -m faceswap` (or the `faceswap` script)."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import webbrowser
from pathlib import Path

from .models import default_models_dir
from .offline import enforce_offline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="faceswap", description="Airgapped GPU face swapper")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1, this PC only)")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--models-dir", type=Path, default=default_models_dir())
    parser.add_argument(
        "--provider", default="auto", help="auto | cuda | directml | coreml | cpu (default: auto, prefers GPU)"
    )
    parser.add_argument("--device-id", type=int, default=0, help="GPU index when you have more than one")
    parser.add_argument("--no-browser", action="store_true", help="don't open the UI in a browser")
    parser.add_argument(
        "--allow-network", action="store_true", help="disable the outbound-network kill switch (not recommended)"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if not args.allow_network:
        enforce_offline()
        logging.info("airgapped mode: outbound network access is blocked for this process")

    from .engine import Engine
    from .server import create_app

    models_dir = args.models_dir.expanduser().resolve()
    try:
        engine = Engine(models_dir, provider=args.provider, device_id=args.device_id)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if engine.active_provider == "CPUExecutionProvider":
        logging.warning("running on CPU. install the `cuda` (NVIDIA) or `directml` extra for GPU acceleration")
    else:
        logging.info("using %s", engine.active_provider)

    import uvicorn

    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}/"
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    print(f"\n  faceswap is running at {url}\n")
    uvicorn.run(create_app(engine, models_dir), host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
