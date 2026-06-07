import json
import io
import piexif
from PIL import Image


def read_metadata(filepath: str) -> dict | None:
    try:
        img = Image.open(filepath)
        exif = img.info.get("exif", b"")
        if not exif:
            return None
        exif_dict = piexif.load(exif)
        raw = exif_dict.get("0th", {}).get(piexif.ImageIFD.ImageDescription)
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def write_metadata(filepath: str, metadata: dict):
    img = Image.open(filepath)
    json_str = json.dumps(metadata, ensure_ascii=False)
    exif_dict = {"0th": {piexif.ImageIFD.ImageDescription: json_str.encode("utf-8")}}
    exif_bytes = piexif.dump(exif_dict)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', exif=exif_bytes)
    buf.seek(0)
    with open(filepath, 'wb') as f:
        f.write(buf.read())
