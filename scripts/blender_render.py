"""Run inside Blender: blender -b scene.blend --python blender_render.py -- config.json"""
import bpy, json, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import atomic_json,digest,load_config,path_for,state,valid_png

args=sys.argv[sys.argv.index("--")+1:]
if not args: raise RuntimeError("config path required after --")
config=load_config(args[0]); r=config["render"]
frames=path_for(config,r["frames_dir"]);manifest_path=path_for(config,r["manifest_file"]);frames.mkdir(parents=True,exist_ok=True)
start,end=int(r["start"]),int(r["end"]);resume=start
while resume<=end and valid_png(frames/f"{resume:06d}.png"): resume+=1
scene=bpy.context.scene;scene.render.engine=r["engine"]
if r["engine"]=="CYCLES":
    prefs=bpy.context.preferences.addons["cycles"].preferences;prefs.compute_device_type=r["device"];prefs.get_devices()
    enabled=[]
    for device in prefs.devices:
        device.use=device.type==r["device"]
        if device.use: enabled.append(device.name)
    if not enabled: raise RuntimeError(f"No {r['device']} render device found")
    scene.cycles.device="GPU";scene.cycles.samples=int(r["samples"]);scene.cycles.use_denoising=bool(r["denoise"])
scene.render.use_persistent_data=True;scene.render.resolution_x=int(r["width"]);scene.render.resolution_y=int(r["height"]);scene.render.resolution_percentage=100
scene.render.fps=int(r["fps"]);scene.render.fps_base=1;scene.frame_start=min(resume,end);scene.frame_end=end
scene.render.image_settings.file_format=r.get("format","PNG");scene.render.image_settings.color_mode=r.get("color_mode","RGB");scene.render.image_settings.color_depth=str(r.get("color_depth","8"));scene.render.image_settings.compression=int(r.get("png_compression",25));scene.render.filepath=str(frames/"######")
began=time.time();last=began
def written(current,*_):
    global last
    now=time.time();done=current.frame_current-start+1;rendered=current.frame_current-resume+1;average=(now-began)/max(1,rendered)
    state(config,"rendering",complete=done,total=end-start+1,last_frame_seconds=now-last,average_frame_seconds=average,eta_seconds=(end-current.frame_current)*average,device=r["device"]);last=now
state(config,"starting",complete=resume-start,total=end-start+1)
bpy.app.handlers.render_write.append(written)
try:
    if resume<=end:bpy.ops.render.render(animation=True)
except Exception as error:
    state(config,"failed",complete=max(0,scene.frame_current-start),total=end-start+1,message=str(error));raise
finally:bpy.app.handlers.render_write.remove(written)
manifest={}
for frame in range(start,end+1):
    path=frames/f"{frame:06d}.png"
    if not valid_png(path):raise RuntimeError(f"missing or invalid frame: {path.name}")
    manifest[path.name]={"bytes":path.stat().st_size,"sha256":digest(path)}
atomic_json(manifest_path,manifest)
state(config,"frames_complete",complete=len(manifest),total=len(manifest),frame_bytes=sum(v["bytes"] for v in manifest.values()),manifest=str(manifest_path))
