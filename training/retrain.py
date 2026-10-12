import argparse, json
from pathlib import Path
from .semantic import train_semantic_detector

def main():
    p=argparse.ArgumentParser(description="Reproduce the shared frozen scene experiment.")
    p.add_argument("--dataset",required=True);p.add_argument("--out",required=True)
    p.add_argument("--allow-ai-labels",action="store_true")
    args=p.parse_args()
    partitions=json.loads((Path(__file__).resolve().parents[1]/"splits.json").read_text())
    result=train_semantic_detector(args.dataset,args.out,allow_ai_labels=args.allow_ai_labels,seed=42,partitions=partitions)
    print(json.dumps({key:result[key] for key in ("status","learned_samples","model_sha256")},indent=2))

if __name__ == "__main__": main()
