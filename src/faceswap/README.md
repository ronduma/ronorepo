# faceswap

An airgapped face swapper that runs on your own GPU. Everything happens on your PC: no accounts, no uploads, and the app blocks its own outbound network traffic while it runs.

- Upload a photo. Every face is found and numbered left to right.
- Upload one or more photos of the new face. If a photo has several people, each face is numbered too.
- Click a face in the photo, then click the face that should replace it. Repeat to swap several faces in one go, each with its own replacement.
- Swap, compare with the original, download, or keep going with the result as the new photo.

Models: SCRFD-10G (detection), ArcFace R50 (identity), inswapper_128 (swap), and optionally GFPGAN 1.4 (sharpens the swapped face). All run through ONNX Runtime on CUDA (NVIDIA) or DirectML (any DirectX 12 GPU on Windows), with CPU as a fallback.

## Requirements

- Python 3.11–3.13 (3.12 recommended) and [uv](https://docs.astral.sh/uv/)
- A GPU:
  - **NVIDIA**: driver 525 or newer. The `cuda` extra installs CUDA 12 and cuDNN as Python packages, so no separate CUDA toolkit is needed. With driver 580+ you can use `cuda13` instead.
  - **AMD / Intel on Windows**: use the `directml` extra.
- About 2.5 GB of disk for Python packages plus 1.1 GB for models.

## Setup

### Option A: install while online, then go offline

```sh
cd src/faceswap
uv sync --extra cuda          # or: --extra cuda13 / --extra directml / --extra cpu
uv run python -m faceswap.download   # fetches and verifies the models into ./models
```

After this nothing needs the internet. Unplug or firewall the PC and run it.

### Option B: the PC never touches the internet

On a machine with internet access, build a bundle for the airgapped PC. The example targets Windows x64 with Python 3.12 and an NVIDIA GPU:

```sh
cd src/faceswap
uv run python -m faceswap.download --models-dir bundle/models
uv export --extra cuda --no-hashes --no-emit-project --no-dev -o bundle/requirements.txt
uvx pip download -r bundle/requirements.txt -d bundle/wheels \
    --only-binary=:all: --platform win_amd64 --python-version 3.12
cp -r faceswap bundle/
```

For Linux use `--platform manylinux_2_28_x86_64`; for AMD/Intel on Windows use `--extra directml`. Also copy the Python 3.12 installer.

Carry `bundle/` over on a USB drive, then on the airgapped PC:

```bat
cd bundle
py -3.12 -m venv .venv
.venv\Scripts\pip install --no-index --find-links wheels -r requirements.txt
.venv\Scripts\python -m faceswap --models-dir models
```

(`source .venv/bin/activate` and `python -m faceswap` on Linux.)

## Run

```sh
uv run python -m faceswap
```

Your browser opens `http://127.0.0.1:7860`. The header shows which device is in use; if it says **CPU only**, see the troubleshooting section below.

| Option | Default | |
| --- | --- | --- |
| `--provider` | `auto` | `cuda`, `directml`, `coreml` or `cpu`. `auto` picks the GPU when one is usable. |
| `--device-id` | `0` | Which GPU, if you have several. |
| `--port` | `7860` | |
| `--host` | `127.0.0.1` | Only this PC can reach the UI. Use `0.0.0.0` to allow your LAN (not recommended). |
| `--models-dir` | `./models` | Or set `FACESWAP_MODELS_DIR`. |
| `--no-browser` | off | Don't open a browser tab. |
| `--allow-network` | off | Turns off the outbound-network kill switch. |

## Using it

1. **Photo to change**: drop or pick an image. Faces get numbered boxes; click one to select it. Tick **find small faces** before uploading for crowds or distant faces.
2. **Replacement face**: drop one or more photos. Click the face to use. It is paired with the face selected on the left, and a small badge shows the pairing.
3. **Swap**: check the list of pairs, choose whether to **enhance** (GFPGAN, adjustable strength) and the output format, then press **Swap**.
4. **Result**: hold **Hold to compare** to see the original, **Download** to save, or **Use as new photo** to swap more faces on top of the result.

You can also paste images with Ctrl+V: the first one becomes the photo to change and later ones become replacement photos.

Best results come from a sharp, front-facing replacement face with even lighting. inswapper works at 128 px, so large faces look soft without enhancement.

## How "airgapped" is enforced

- The app never downloads anything. Models come from `python -m faceswap.download`, which you run separately. It verifies SHA-256 checksums.
- On startup the server patches Python's socket layer so any DNS lookup or outbound connection raises an error. That includes connections to other programs on this PC, such as a local proxy or VPN client that could relay traffic. Only the local web UI works. Proxy environment variables are also cleared.
- The server binds to `127.0.0.1` by default, and the UI loads no external fonts, scripts or CDNs.
- Uploaded images stay in memory (the last 32) and are never written to disk. Results are only saved when you download them.

For a hard guarantee, also block the Python executable in your OS firewall or physically disconnect the PC.

## Troubleshooting

**Header says "CPU only"**
- Check that you installed a GPU extra (`cuda`, `cuda13` or `directml`). Only one can be installed at a time; `uv sync --extra cuda` removes the others.
- `cuda13` needs driver 580+. On older drivers use `cuda`.
- NVIDIA: run `nvidia-smi` to confirm the driver works. Then run `uv run python -c "import onnxruntime as o; o.preload_dlls(); print(o.get_available_providers())"`, which should list `CUDAExecutionProvider`.
- Force a provider with `--provider cuda` to see the actual error.

**"No faces found"**: try **find small faces**, or crop closer to the face. Extreme angles (profile views) and heavy occlusion aren't detected reliably.

**Hair from the replacement shows on the forehead**: expected for very different hairlines. A replacement photo with hair pulled back works best.

## Tests

```sh
uv sync --extra cpu
uv run pytest                                   # unit tests
FACESWAP_TEST_IMAGE=/path/to/group.jpg uv run pytest   # plus end-to-end tests with the real models
```

## Responsible use

Only swap faces of people who have agreed to it, and don't use results to deceive, harass or impersonate anyone. Many places have laws against non-consensual synthetic imagery. The upstream model licences (insightface, inswapper, GFPGAN) are for non-commercial research use.
