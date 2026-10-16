"""Bounded local image registry; no arbitrary files or network URLs."""
from pathlib import Path
import re
import tempfile
import warnings

from PIL import Image

from shared_mvp.contracts import Invalid
from shared_mvp.domain import require


def root(pid):
    path = Path(tempfile.gettempdir()) / 'sea-ai-mvp-assets' / pid
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def resolve(pid, name):
    require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]+\.(png|jpg|jpeg)', name) is not None,
            'Asset must be an approved local image filename, not a path or URL')
    directory = root(pid)
    path = (directory / name).resolve()
    require(path.parent == directory and path.is_file() and not (directory / name).is_symlink(), 'Unknown or unsafe asset')
    require(path.stat().st_size <= 5 * 1024 * 1024, 'Image exceeds 5 MiB')
    return path


def read(pid, record):
    path = resolve(pid, record['asset_path'])
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path) as opened:
                require(opened.format in {'PNG', 'JPEG'}, 'Unsupported actual image format')
                require(opened.width * opened.height <= 4_000_000, 'Image pixel limit exceeded')
                require((opened.width, opened.height) == (record['width'], record['height']), 'Declared dimensions do not match image')
                opened.load()
                return opened.copy()
    except (OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise Invalid('Corrupt or oversized image') from None


def validate_images(pid, data):
    require(len(data['images']) <= 20, 'At most 20 images')
    for image in data['images']:
        read(pid, image)
