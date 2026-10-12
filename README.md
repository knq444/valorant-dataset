# CORTEX ARENA — public VALORANT research dataset

Original annotations, source references, hashes, frozen whole-match partitions,
own scene-model weights, and a standalone NumPy/Pillow trainer for everyone.
No access to the private application repository is needed.

## What the model learns

The model recognizes broadcast scenes: gameplay POV, replay, tactical map,
broadcast break and unknown. It does **not** learn whether a professional's
decision was correct. Labels inspected by AI remain `ai_inspected`; automatic
move proposals remain `pending`. Neither is independent human ground truth.
The model card and report record the actual evaluation and its limitations.
Move grades are conditional experimental rubric calculations, not human labels
or win probabilities. A broadcast cannot expose every decision of ten players.

## Use the shared model

```sh
python -m pip install -r requirements.txt
python -m training.predict --model models/scene/model.npz --frame YOUR_LOCAL_FRAME.jpg
python -m training.verify
```

The repository intentionally contains no videos, images, audio, commentary
transcripts, personal notes, credentials or application database. Obtain source
media locally where permitted; references are not a redistribution license.
The media must match each registered SHA. If an encoding has changed, use a new
cohort and new inspection rather than silently transferring these labels.

## Reconstruct and train

Create a **local, uncommitted** `local-media.json` mapping each source URL to
the absolute path of the matching local video. Install FFmpeg or pass its path.

```sh
python -m training.reconstruct --media-map local-media.json --out local-dataset
python -m training.retrain --dataset local-dataset/labels.jsonl --out local-model --allow-ai-labels
```

Reconstruction verifies source and frame hashes before publishing the dataset.
Training uses the frozen whole-match partitions in `splits.json`; frames and
replays from a held-out match never enter training. Model output must be new.
Numerical libraries/FFmpeg/JPEG versions can affect exact reproduction.

## Contribute

Open a pull request with original JSONL annotations and source/hash/PTS evidence.
Use `CONTRIBUTING.md`. Do not upload third-party media or private notes. Explain
what was observed, inferred and uncertain. A maintainer reviews contributions;
the public model does not update automatically on a pull request. Independent
human review must identify a reviewer different from the annotator. AI must not
claim human attestation. Tactical judgments and scene labels are separate tasks.

## Licenses and attribution

Original annotations and our own model parameters: **CC BY 4.0**, to the extent
we control the rights. Attribution: "CORTEX ARENA contributors — valorant-dataset",
with this repository URL and the release identifier in `manifest.json`.
Standalone original code: **MIT**. Third-party sources, trademarks and media
retain their own rights; neither license grants rights to those materials.
VALORANT and Riot Games are trademarks of Riot Games. This independent research
project is not endorsed or sponsored by Riot Games or Chess.com.

License text: https://creativecommons.org/licenses/by/4.0/legalcode.en

## This release

535 scene annotations from 6 whole-match groups; 535 AI inspections and 0 declared independent human reviews.

131 machine event proposals across 9246 sampled timeline windows. Proposals retain definitive `Indeterminado` / null scores; any resource-rubric points are experimental.
Evaluation: [scene model card](models/scene/MODEL_CARD.md), [full report](models/scene/report.json).
