# Contributions

Only submit annotations you can share publicly. Never include videos, screenshots,
audio, full copied commentary, credentials, personal notes or absolute local paths.
Add source URL, media SHA-256, safe relative frame path, frame SHA, timestamp,
observer/player scope, label, annotator and review provenance following
annotations/scenes.jsonl. Unknown is valid; do not invent labels to fill gaps.
Check `python -m training.verify` before submitting a pull request.

Preserve frozen match partitions. New test matches cannot be used for fitting
or selecting thresholds. A new annotation cohort needs a separate version and
evaluation. Human verification requires an independent human reviewer and date;
AI inspection is explicitly AI, never human. Move proposals are not scene labels.
By submitting original annotations, contributors offer them under CC BY 4.0;
original code contributions are MIT. No third-party media rights are implied.
