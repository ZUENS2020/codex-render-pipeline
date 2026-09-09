#!/usr/bin/env python3
import csv,json,os,shutil,subprocess,sys,threading,time
from collections import deque
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import load_config,path_for

config=load_config(sys.argv[1]);render=config["render"];delivery=config["delivery"];mon=config["monitor"]
frames=path_for(config,render["frames_dir"]);render_state=path_for(config,render["state_file"]);manifest=path_for(config,render["manifest_file"]);delivery_state=path_for(config,delivery["state_file"]);delivery_frames=path_for(config,delivery["frames_dir"]);dashboard=path_for(config,mon["dashboard_dir"])
history=deque(maxlen=240);lock=threading.Lock();snapshot={}
def read_json(path):
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:return {}
def gpu():
    try:
        raw=subprocess.check_output(["nvidia-smi","--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit,clocks.sm","--format=csv,noheader,nounits"],timeout=8,text=True);row=next(csv.reader(raw.splitlines()));keys=["name","utilization","memory_used_mib","memory_total_mib","temperature_c","power_w","power_limit_w","clock_mhz"]
        return dict(zip(keys,[row[0].strip()]+[float(v.strip()) for v in row[1:]]))
    except Exception:return {}
def system_info():
    result={"cpu_percent":None,"ram_total_bytes":None,"ram_used_bytes":None,"processes":[]}
    try:
        if os.name=="nt":
            script="$os=Get-CimInstance Win32_OperatingSystem;$cpu=Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter \"Name='_Total'\";$p=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -in @('blender.exe','ffmpeg.exe','python.exe','pythonw.exe')}|ForEach-Object {@{pid=$_.ProcessId;name=$_.Name;ram_bytes=[double]$_.WorkingSetSize}});@{cpu=$cpu.PercentProcessorTime;total=[double]$os.TotalVisibleMemorySize*1024;used=([double]$os.TotalVisibleMemorySize-[double]$os.FreePhysicalMemory)*1024;processes=$p}|ConvertTo-Json -Depth 3 -Compress"
            value=json.loads(subprocess.check_output(["powershell.exe","-NoProfile","-Command",script],timeout=12,text=True,encoding="utf-8-sig"));result.update(cpu_percent=value.get("cpu"),ram_total_bytes=value.get("total"),ram_used_bytes=value.get("used"),processes=value.get("processes") or [])
        else:
            memory={line.split(":",1)[0]:int(line.split()[1])*1024 for line in Path("/proc/meminfo").read_text().splitlines()} if Path("/proc/meminfo").exists() else {}
            if sys.platform=="darwin":
                total=int(subprocess.check_output(["sysctl","-n","hw.memsize"],text=True).strip());vm=subprocess.check_output(["vm_stat"],text=True).splitlines();page_size=int(vm[0].split()[-2]);pages={line.split(":",1)[0]:int(line.split(":",1)[1].strip().rstrip(".")) for line in vm[1:]};available=(pages.get("Pages free",0)+pages.get("Pages inactive",0)+pages.get("Pages speculative",0))*page_size;memory={"MemTotal":total,"MemAvailable":available}
            processes=subprocess.check_output(["ps","-eo","pid=,comm=,rss="],timeout=8,text=True).splitlines();selected=[]
            for line in processes:
                fields=line.split()
                if len(fields)>=3 and any(x in fields[1].lower() for x in ("blender","ffmpeg","python")):selected.append({"pid":int(fields[0]),"name":fields[1],"ram_bytes":int(fields[2])*1024})
            result.update(cpu_percent=min(100,os.getloadavg()[0]/max(1,os.cpu_count() or 1)*100),ram_total_bytes=memory.get("MemTotal"),ram_used_bytes=memory.get("MemTotal",0)-memory.get("MemAvailable",0),processes=selected)
    except Exception:pass
    return result
def recent_logs(directory):
    lines=[]
    try:
        for path in sorted(directory.glob("*.log"),key=lambda item:item.stat().st_mtime,reverse=True)[:3]:
            lines.extend(path.read_text(encoding="utf-8",errors="replace").splitlines()[-5:])
    except OSError:pass
    return lines[-15:]
def update():
    global snapshot
    while True:
        delivery_value=read_json(delivery_state);render_value=read_json(render_state)
        state=delivery_value if delivery_value.get("updated_at",0)>render_value.get("updated_at",0) else render_value
        source_frames=delivery_frames if state is delivery_value and delivery_frames.exists() else frames
        files=list(source_frames.glob("[0-9][0-9][0-9][0-9][0-9][0-9].png"));count=len(files);size=sum(p.stat().st_size for p in files);total=int(render["end"])-int(render["start"])+1;disk=shutil.disk_usage(config["_root"]);g=gpu();entry={"ts":time.time(),"complete":state.get("complete",count),"gpu":g.get("utilization"),"bytes":size};history.append(entry)
        complete=state.get("complete",count);declared_total=state.get("total",total);sysinfo=system_info()
        value={"schema_version":1,"generated_at":time.time(),"phase":state.get("stage","idle"),"status":state,"progress":{"complete":complete,"total":declared_total,"percent":100*complete/max(1,declared_total),"remaining":max(0,declared_total-complete),"last_frame_seconds":state.get("last_frame_seconds"),"average_frame_seconds":state.get("average_frame_seconds"),"eta_seconds":state.get("eta_seconds"),"downloaded_bytes":size,"expected_bytes":state.get("expected_bytes")},"gpu":g,"system":sysinfo,"storage":{"free_bytes":disk.free,"used_bytes":disk.used,"total_bytes":disk.total,"frame_bytes":size,"frame_file_count":count},"output":{"width":render["width"],"height":render["height"],"fps":render["fps"],"samples":render["samples"],"project":config["project"],"outputs":state.get("outputs")},"history":list(history),"logs":recent_logs(path_for(config,delivery["state_file"]).parent)}
        with lock:snapshot=value
        time.sleep(10)
threading.Thread(target=update,daemon=True).start()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def send_file(self,path,mime):
        try:body=path.read_bytes()
        except OSError:self.send_error(404);return
        self.send_response(200);self.send_header("Content-Type",mime);self.send_header("Content-Length",str(len(body)));self.send_header("Cache-Control","no-cache");self.end_headers();self.wfile.write(body)
    def do_GET(self):
        route=self.path.split("?",1)[0]
        if route=="/api/metrics":
            with lock:body=json.dumps(snapshot,ensure_ascii=False).encode()
            self.send_response(200 if snapshot else 503);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(body);return
        if route=="/api/status":
            use_delivery=delivery_state.exists() and (not render_state.exists() or delivery_state.stat().st_mtime>render_state.stat().st_mtime)
            self.send_file(delivery_state if use_delivery else render_state,"application/json");return
        if route=="/manifest.json":self.send_file(manifest,"application/json");return
        if route.startswith("/frames/"):
            name=route[8:]
            if len(name)!=10 or not name[:6].isdigit() or name[6:]!=".png":self.send_error(404);return
            self.send_file(frames/name,"image/png");return
        if route=="/preview.png":
            candidates=sorted(frames.glob("[0-9][0-9][0-9][0-9][0-9][0-9].png"));self.send_file(candidates[-1],"image/png") if candidates else self.send_error(404);return
        if route in ("/","/index.html"):self.send_file(dashboard/"index.html","text/html; charset=utf-8");return
        self.send_error(404)
ThreadingHTTPServer((mon.get("host","127.0.0.1"),int(mon.get("port",8767))),Handler).serve_forever()
