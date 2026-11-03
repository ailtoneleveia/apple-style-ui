"""ambiente.py: sem numpy, pillow ou opencv no python3 da pessoa, roda o script de novo no ambiente do produto
(~/.apple-style-ui/venv, criado pelo preparar.py). Importe antes do numpy; importado por outro script, refaz aquele."""
import os, sys

_VENV = os.path.expanduser("~/.apple-style-ui/venv")
try:
    import numpy, PIL, cv2  # noqa: F401,E401
except ImportError:
    if os.path.exists(f"{_VENV}/bin/python") and sys.prefix != _VENV:
        os.execv(f"{_VENV}/bin/python", [f"{_VENV}/bin/python", *sys.argv])
