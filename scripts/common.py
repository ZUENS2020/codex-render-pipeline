import hashlib, json, os, struct, time, zlib
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]

def load_config(filename):
    source = Path(filename).expanduser().resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    root = Path(data["project"].get("root", "."))
    if not root.is_absolute(): root = (source.parent / root).resolve()
    data["_config"] = source; data["_root"] = root
    return data

def path_for(config, value):
    if str(value).startswith("plugin:"): return PLUGIN / str(value)[7:]
    path = Path(value).expanduser()
    return path if path.is_absolute() else config["_root"] / path

def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)

def state(config, stage, **values):
    target = values.pop("state_path", path_for(config, config["render"]["state_file"]))
    payload = {"schema_version":1,"stage":stage,"project":config["project"]["name"],
               "revision":config["project"]["revision"],"updated_at":time.time(),**values}
    atomic_json(target, payload); return payload

def valid_png(path):
    try:
        with Path(path).open("rb") as stream:
            if stream.read(8) != b"\x89PNG\r\n\x1a\n": return False
            while True:
                header = stream.read(8)
                if len(header) != 8: return False
                size, kind = struct.unpack(">I4s", header)
                data, crc = stream.read(size), stream.read(4)
                if len(data) != size or len(crc) != 4: return False
                if zlib.crc32(kind + data) & 0xffffffff != struct.unpack(">I", crc)[0]: return False
                if kind == b"IEND": return True
    except OSError: return False

def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""): sha.update(chunk)
    return sha.hexdigest()

def validate(config):
    errors=[]
    for group in ("project","render","monitor","remote","delivery"):
        if group not in config: errors.append(f"missing section: {group}")
    if errors: return errors
    render=config["render"]; delivery=config["delivery"]
    for key in ("start","end","fps","width","height","samples"):
        if int(render.get(key,0)) <= 0: errors.append(f"render.{key} must be positive")
    if render.get("start",1)>render.get("end",0): errors.append("render.start exceeds render.end")
    if render.get("format","PNG") != "PNG": errors.append("render.format must be PNG for resumable verification")
    for key in ("frames_dir","state_file","manifest_file"):
        if not render.get(key): errors.append(f"render.{key} is required")
    if not delivery.get("master",{}).get("filename"): errors.append("delivery.master.filename is required")
    names=[delivery.get("master",{}).get("filename")]+[v.get("filename") for v in delivery.get("variants",[])]
    if len(names)!=len(set(names)): errors.append("output filenames must be unique")
    return errors
