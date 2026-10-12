from hashlib import sha256
import json
from pathlib import Path
from .semantic import load_semantic_dataset, SemanticDetector

def main():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/"manifest.json").read_text())
    for row in manifest["files"]:
        path=(root/row["path"]).resolve()
        if not path.is_relative_to(root) or path.stat().st_size!=row["bytes"] or sha256(path.read_bytes()).hexdigest()!=row["sha256"]:
            raise ValueError("Release file integrity failed")
    dataset=load_semantic_dataset(root/"annotations/scenes.jsonl",verify_files=False)
    model=SemanticDetector.load(root/"models/scene/model.npz")
    if model.metadata["dataset_sha256"]!=dataset.sha256: raise ValueError("Model/dataset binding failed")
    print(json.dumps({"verified_files":len(manifest["files"]),"dataset":dataset.audit()},indent=2))

if __name__ == "__main__": main()
