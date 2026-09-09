#!/usr/bin/env python3
import argparse, json, shutil, sys
from pathlib import Path
from common import load_config, path_for, validate

def main():
    parser=argparse.ArgumentParser(description="Configure and inspect a Codex render pipeline")
    sub=parser.add_subparsers(dest="command",required=True)
    init=sub.add_parser("init");init.add_argument("--root",required=True);init.add_argument("--force",action="store_true")
    check=sub.add_parser("validate");check.add_argument("config")
    show=sub.add_parser("paths");show.add_argument("config")
    args=parser.parse_args()
    if args.command=="init":
        root=Path(args.root).expanduser().resolve();root.mkdir(parents=True,exist_ok=True)
        target=root/"render-pipeline.json"
        if target.exists() and not args.force: raise SystemExit(f"exists: {target}")
        template=Path(__file__).resolve().parents[1]/"render-pipeline.example.json"
        shutil.copyfile(template,target);print(target);return
    config=load_config(args.config);errors=validate(config)
    if errors:
        print(json.dumps({"valid":False,"errors":errors},indent=2));raise SystemExit(2)
    if args.command=="validate": print(json.dumps({"valid":True,"project":config["project"]},indent=2));return
    keys={"blend":config["project"]["blend_file"],**{k:config["render"][k] for k in ("frames_dir","state_file","manifest_file")},**{"delivery_"+k:config["delivery"][k] for k in ("frames_dir","state_file","output_dir")}}
    print(json.dumps({k:str(path_for(config,v)) for k,v in keys.items()},indent=2))
if __name__=="__main__": main()
