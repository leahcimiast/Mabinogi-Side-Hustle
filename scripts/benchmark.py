"""Offline capture-independent benchmark. Never sends input or registers hotkeys."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import statistics
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.capture import reference
from app.inventory_recognition import preview
from app.whitelist import load

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('image',type=Path)
    parser.add_argument('--runs',type=int,default=3)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if not 1<=args.runs<=10:
        parser.error('--runs must be between 1 and 10')
    root=Path(__file__).resolve().parents[1]
    image,_=reference(args.image)
    entries=load(root/'app/default_whitelist.json')
    results=[]
    for _ in range(args.runs):
        result=preview(image,entries,root/'scripts/ocr.ps1')
        results.append(dict(timings=result.timings,exact=sum(x.kind=='quest' for x in result.detections),
                            known_counts=sum(x.kind=='quest' and x.count is not None for x in result.detections),
                            candidate_reviews=len(result.reviews)))
    print(f"Median: {statistics.median(x['timings']['total_ms'] for x in results)/1000:.3f} seconds")
    if args.output:
        args.output.write_text(json.dumps(results,indent=2),encoding='utf-8')
