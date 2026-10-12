import argparse, json
from .semantic import SemanticDetector

def main():
    parser=argparse.ArgumentParser(description="Shared scene model; no tactical grade.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--frame", required=True)
    args=parser.parse_args()
    print(json.dumps(SemanticDetector.load(args.model).predict(args.frame), indent=2))

if __name__ == "__main__": main()
