"""Input and output formats for offline calibration."""

import json
import os
import tempfile
from pathlib import Path

from .geometry import checked_transform


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError(f"{Path(path).name} 必须是一个 JSON 对象。")
    return value


def write_json(path, value):
    """Write UTF-8 JSON via a temporary file in the destination directory."""
    path = Path(path)
    payload = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(payload)
        try:
            os.replace(temporary, path)
        except PermissionError:
            # Some restricted locations allow new files but forbid renaming them.
            # Exclusive creation keeps a previously written result intact.
            with path.open("x", encoding="utf-8") as output:
                try:
                    output.write(payload)
                    output.flush()
                except OSError:
                    output.close()
                    path.unlink(missing_ok=True)
                    raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def list_images(directory):
    return sorted(
        (p for p in Path(directory).iterdir() if p.is_file() and p.suffix.casefold() in IMAGE_EXTENSIONS),
        key=lambda path: path.name.casefold(),
    )


def load_pose_pairs(path, image_directory):
    manifest = read_json(path)
    if manifest.get("frame") != "gripper_to_base" or manifest.get("length_unit") != "mm":
        raise ValueError("位姿文件必须声明 frame 为 gripper_to_base，length_unit 为 mm。")
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("位姿文件的 samples 必须是包含图像名和矩阵的非空列表。")
    files = list_images(image_directory)
    images = {file.name.casefold(): file for file in files}
    if len(files) != len(images):
        raise ValueError("图像目录存在仅大小写不同的重名文件。")
    pairs = []
    seen = set()
    for index, sample in enumerate(samples, 1):
        name = sample.get("image") if isinstance(sample, dict) else None
        if (
            not isinstance(name, str)
            or not name
            or Path(name).name != name
            or any(character in name for character in '\\/:*?"<>|\0')
            or Path(name).suffix.casefold() not in IMAGE_EXTENSIONS
        ):
            raise ValueError(f"第 {index} 项的 image 必须是不含目录的图像文件名。")
        if name.casefold() in seen:
            raise ValueError(f"位姿列表有重复图像名 {name}。")
        key = name.casefold()
        seen.add(key)
        pairs.append((images.get(key, Path(image_directory) / name), checked_transform(sample.get("matrix"), name)))
    pairs.extend((file, None) for key, file in images.items() if key not in seen)
    return pairs
