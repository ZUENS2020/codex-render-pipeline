#!/usr/bin/env python3
import argparse, json, os, subprocess, time, urllib.request
from pathlib import Path
from common import atomic_json,digest,load_config,path_for,validate

def request_json(base,path,timeout):
    with urllib.request.urlopen(base.rstrip("/")+path,timeout=timeout) as response:return json.load(response)
def write_state(config,stage,**values):
    target=path_for(config,config["delivery"]["state_file"])
    payload={"schema_version":1,"stage":stage,"project":config["project"]["name"],"revision":config["project"]["revision"],"updated_at":time.time(),**values};atomic_json(target,payload)
def run(command,log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open("w",encoding="utf-8") as output:subprocess.run(command,stdout=output,stderr=subprocess.STDOUT,check=True)
def hashes(path):return [line.rsplit(",",1)[1].strip() for line in path.read_text().splitlines() if line and not line.startswith("#")]

def main():
    parser=argparse.ArgumentParser();parser.add_argument("config");args=parser.parse_args()
    config=load_config(args.config);errors=validate(config)
    if errors:raise RuntimeError("; ".join(errors))
    d=config["delivery"];r=config["render"];base=config["remote"]["base_url"];timeout=int(config["remote"].get("request_timeout_seconds",90));poll=int(config["remote"].get("poll_seconds",30))
    dest=path_for(config,d["frames_dir"]);out=path_for(config,d["output_dir"]);logs=path_for(config,d["state_file"]).parent;dest.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    total_frames=int(r["end"])-int(r["start"])+1
    try:
        while True:
            try:
                remote=request_json(base,"/api/status",timeout)
                write_state(config,"waiting_render",server_stage=remote.get("stage"),server_complete=remote.get("complete",0),total=total_frames)
                if remote.get("stage")=="frames_complete":break
            except Exception as error:write_state(config,"waiting_render",message="remote unavailable; retrying",error=str(error))
            time.sleep(poll)
        manifest=request_json(base,"/manifest.json",timeout);assert len(manifest)==total_frames
        expected=sum(item["bytes"] for item in manifest.values());atomic_json(logs/"source-manifest.json",manifest);downloaded=0
        for index,(name,item) in enumerate(manifest.items(),1):
            target=dest/name
            if target.exists() and target.stat().st_size==item["bytes"] and digest(target)==item["sha256"]:downloaded+=item["bytes"];continue
            partial=target.with_suffix(target.suffix+".partial")
            for attempt in range(10):
                try:
                    with urllib.request.urlopen(base.rstrip("/")+"/frames/"+name,timeout=timeout) as source,partial.open("wb") as sink:
                        while chunk:=source.read(1024*1024):sink.write(chunk)
                    if partial.stat().st_size!=item["bytes"] or digest(partial)!=item["sha256"]:raise RuntimeError("hash mismatch")
                    os.replace(partial,target);downloaded+=item["bytes"];write_state(config,"downloading",complete=index,total=total_frames,downloaded_bytes=downloaded,expected_bytes=expected);break
                except Exception:
                    if attempt==9:raise
                    time.sleep(min(60,5*(attempt+1)))
        write_state(config,"verifying",complete=0,total=total_frames,expected_bytes=expected)
        for index,(name,item) in enumerate(manifest.items(),1):
            target=dest/name
            if target.stat().st_size!=item["bytes"] or digest(target)!=item["sha256"]:raise RuntimeError(f"source verification failed: {name}")
            if index%25==0:write_state(config,"verifying",complete=index,total=total_frames,expected_bytes=expected)
        ffmpeg=str(d["ffmpeg"]);ffprobe=str(d["ffprobe"]);pattern=str(dest/"%06d.png");master=d["master"];master_final=out/master["filename"];master_partial=master_final.with_name(master_final.stem+".partial"+master_final.suffix)
        common=[ffmpeg,"-v","error","-y","-framerate",str(r["fps"]),"-start_number",str(r["start"]),"-i",pattern,"-frames:v",str(total_frames),"-an"]
        write_state(config,"assembling_master",complete=total_frames,total=total_frames,output=str(master_final))
        run(common+["-c:v",master["codec"],"-pix_fmt",master["pixel_format"],str(master_partial)],logs/"assemble-master.log")
        if d.get("verify_master_pixels",True):
            write_state(config,"verifying_master",complete=0,total=total_frames,output=str(master_final))
            source_hash=logs/"source-pixels.sha256";master_hash=logs/"master-pixels.sha256"
            run([ffmpeg,"-v","error","-y","-framerate",str(r["fps"]),"-i",pattern,"-frames:v",str(total_frames),"-pix_fmt","rgb24","-f","framehash","-hash","sha256",str(source_hash)],logs/"hash-source.log")
            run([ffmpeg,"-v","error","-y","-i",str(master_partial),"-frames:v",str(total_frames),"-pix_fmt","rgb24","-f","framehash","-hash","sha256",str(master_hash)],logs/"hash-master.log")
            if hashes(source_hash)!=hashes(master_hash):raise RuntimeError("uncompressed master pixel verification failed")
        os.replace(master_partial,master_final)
        outputs={"master":{"path":str(master_final),"bytes":master_final.stat().st_size}}
        for number,variant in enumerate(d.get("variants",[]),1):
            final=out/variant["filename"];partial=final.with_name(final.stem+".partial"+final.suffix)
            write_state(config,"compressing",variant=number,variant_count=len(d["variants"]),output=str(final))
            command=[ffmpeg,"-v","error","-y","-i",str(master_final),"-frames:v",str(total_frames),"-an","-c:v",variant["codec"],"-preset",variant.get("preset","medium"),"-crf",str(variant.get("crf",18)),"-pix_fmt",variant.get("pixel_format","yuv420p")]
            if variant.get("movflags"):command += ["-movflags",variant["movflags"]]
            run(command+[str(partial)],logs/f"compress-{number}.log")
            write_state(config,"validating_variant",variant=number,variant_count=len(d["variants"]),output=str(final))
            run([ffmpeg,"-v","error","-i",str(partial),"-f","null","-"],logs/f"decode-{number}.log")
            metadata=json.loads(subprocess.check_output([ffprobe,"-v","error","-select_streams","v:0","-show_entries","stream=width,height,r_frame_rate,nb_frames,duration","-of","json",str(partial)]))["streams"][0]
            if int(metadata["width"])!=int(r["width"]) or int(metadata["height"])!=int(r["height"]) or int(metadata["nb_frames"])!=total_frames:raise RuntimeError(f"variant metadata failed: {final.name}")
            os.replace(partial,final);outputs[f"variant_{number}"]={"path":str(final),"bytes":final.stat().st_size,"metadata":metadata}
        write_state(config,"complete",complete=total_frames,total=total_frames,pixel_hash_verified=bool(d.get("verify_master_pixels",True)),outputs=outputs)
    except Exception as error:write_state(config,"failed",message=str(error));raise
if __name__=="__main__":main()
