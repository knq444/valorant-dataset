"""Trainable, pixel-only broadcast-state detector with auditable supervision.

The detector recognizes observable image classes. Its class scores are not
probabilities of winning a round, and it never assigns tactical move quality.
AI-inspected labels support an explicit exploratory experiment; only independent
human review supports the ``human_reviewed`` supervision designation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlsplit

import numpy as np
from PIL import Image

STATES = ("gameplay_pov", "tactical_map", "replay", "broadcast_break", "unknown")
EVENTS = ("none", "kill_feed_update", "ability_effect", "spike_plant", "spike_defuse",
          "weapon_fire", "reload", "player_death", "unknown")
FEATURE_VERSION = "spatial_rgb_edges_v1"


class SemanticError(ValueError):
    """Invalid data, unsupported checkpoint, or insufficient evidence."""


def _object(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise SemanticError(f"Expected fields {sorted(required)}; allowed optional {sorted(optional)}")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise SemanticError(f"{name}: nonempty text without control characters required")
    return value.strip()


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise SemanticError(f"{name}: finite nonnegative number required")
    return float(value)


def _hash(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise SemanticError("SHA-256 must be 64 lowercase hexadecimal characters")
    return value


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise SemanticError(f"Duplicate JSON field {key}")
        value[key] = item
    return value


def _source_identity(parsed):
    host = parsed.hostname.casefold().rstrip(".")
    provider_id = None
    if host == "youtu.be":
        provider_id = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}:
        parts = parsed.path.strip("/").split("/")
        if parts == ["watch"]:
            ids = parse_qs(parsed.query).get("v", [])
            if len(ids) != 1:
                raise SemanticError("YouTube source must identify exactly one video")
            provider_id = ids[0]
        elif len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
            provider_id = parts[1]
    if provider_id:
        if any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in provider_id):
            raise SemanticError("Malformed YouTube video identifier")
        return "youtube:" + provider_id
    return parsed._replace(fragment="", netloc=parsed.netloc.casefold()).geturl()


def _frame(value, base, verify_files, previous=False):
    _object(value, {"path", "sha256", "timestamp_s"} if previous else {"path", "sha256"})
    name = _text(value["path"], "frame.path")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or ":" in name or "\\" in name:
        raise SemanticError("Frame path must be a safe relative POSIX path")
    target = (base / relative).resolve()
    if not target.is_relative_to(base.resolve()):
        raise SemanticError("Frame escapes the dataset directory")
    _hash(value["sha256"])
    if verify_files:
        if not target.is_file() or sha256(target.read_bytes()).hexdigest() != value["sha256"]:
            raise SemanticError(f"Missing frame or frame hash mismatch: {name}")
        try:
            with Image.open(target) as image:
                image.verify()
        except (OSError, ValueError) as exc:
            raise SemanticError(f"Invalid image: {name}") from exc
    if previous:
        _number(value["timestamp_s"], "previous_frame.timestamp_s")


@dataclass(frozen=True)
class SemanticDataset:
    records: tuple[dict, ...]
    base: Path
    sha256: str
    source_path: Path

    def audit(self):
        return {"samples": len(self.records), "matches": len({r["match_id"] for r in self.records}),
                "sources": len({r["source_sha256"] for r in self.records}),
                "human_verified": sum(r["verification"]["status"] == "human_verified" for r in self.records),
                "ai_inspected": sum(r["verification"]["status"] == "ai_inspected" for r in self.records),
                "pending": sum(r["verification"]["status"] == "pending" for r in self.records),
                "dataset_sha256": self.sha256}


def load_semantic_dataset(path: str | Path, *, verify_files: bool = True) -> SemanticDataset:
    """Load strict JSONL and verify actual frame bytes, provenance and label review."""
    path = Path(path).resolve()
    raw = path.read_bytes()
    records, ids, frames, sources, source_urls = [], set(), {}, {}, {}
    for line_number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_unique_pairs,
                             parse_constant=lambda value: (_ for _ in ()).throw(SemanticError(value)))
            _object(row, {"schema_version", "sample_id", "match_id", "source_url", "source_sha256",
                          "timestamp_s", "frame", "visibility_scope", "state", "annotator",
                          "verification", "evidence"}, {"previous_frame", "event_label"})
            if type(row["schema_version"]) is not int or row["schema_version"] != 1:
                raise SemanticError("schema_version must be integer 1")
            for field in ("sample_id", "match_id", "evidence"):
                _text(row[field], field)
            if row["sample_id"] in ids:
                raise SemanticError("Duplicate sample_id")
            ids.add(row["sample_id"])
            parsed = urlsplit(_text(row["source_url"], "source_url"))
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise SemanticError("A public HTTPS source without credentials is required")
            _hash(row["source_sha256"])
            if row["source_sha256"] in sources and sources[row["source_sha256"]] != row["match_id"]:
                raise SemanticError("One source cannot belong to multiple match IDs")
            sources[row["source_sha256"]] = row["match_id"]
            canonical_url = _source_identity(parsed)
            if canonical_url in source_urls and source_urls[canonical_url] != row["match_id"]:
                raise SemanticError("One source URL cannot belong to multiple match IDs")
            source_urls[canonical_url] = row["match_id"]
            _number(row["timestamp_s"], "timestamp_s")
            if row["state"] not in STATES or row.get("event_label", "unknown") not in EVENTS:
                raise SemanticError("Unsupported visual state or event label")
            if row["visibility_scope"] not in {"observer_truth", "player_observation"}:
                raise SemanticError("Explicit observer_truth or player_observation scope required")
            _frame(row["frame"], path.parent, verify_files)
            previous = row.get("previous_frame")
            if previous:
                _frame(previous, path.parent, verify_files, previous=True)
                if previous["timestamp_s"] >= row["timestamp_s"]:
                    raise SemanticError("Temporal features require a strictly earlier frame")
                if row["timestamp_s"] - previous["timestamp_s"] > 10:
                    raise SemanticError("Previous frame must be within ten seconds")
            frame_key = row["frame"]["sha256"]
            if frame_key in frames:
                raise SemanticError("Duplicate frame bytes would contaminate the split")
            frames[frame_key] = row["sample_id"]
            _object(row["annotator"], {"name", "type"})
            _text(row["annotator"]["name"], "annotator.name")
            if row["annotator"]["type"] not in {"ai", "human"}:
                raise SemanticError("annotator.type must be ai or human")
            verification = _object(row["verification"], {"status", "reviewer", "reviewer_type", "reviewed_at"})
            status = verification["status"]
            if status == "pending":
                if any(verification[key] is not None for key in ("reviewer", "reviewer_type", "reviewed_at")):
                    raise SemanticError("Pending labels cannot claim a review")
            elif status in {"ai_inspected", "human_verified"}:
                reviewer = _text(verification["reviewer"], "reviewer")
                wanted_type = "human" if status == "human_verified" else "ai"
                if verification["reviewer_type"] != wanted_type:
                    raise SemanticError("Review status and reviewer type disagree")
                if status == "human_verified" and reviewer.casefold() == row["annotator"]["name"].casefold():
                    raise SemanticError("Human review must be independent of the annotator")
                date = datetime.fromisoformat(_text(verification["reviewed_at"], "reviewed_at").replace("Z", "+00:00"))
                if date.tzinfo is None or date.utcoffset().total_seconds() != 0:
                    raise SemanticError("Review date must include UTC timezone")
            else:
                raise SemanticError("Unsupported review status")
            records.append(row)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise SemanticError(f"Line {line_number}: {exc}") from exc
    return SemanticDataset(tuple(records), path.parent, sha256(raw).hexdigest(), path)


def _image_array(frame):
    if isinstance(frame, (str, Path)):
        with Image.open(frame) as image:
            return np.asarray(image.convert("RGB").resize((64, 36), Image.Resampling.BILINEAR), dtype=np.float64) / 255
    if isinstance(frame, Image.Image):
        return np.asarray(frame.convert("RGB").resize((64, 36), Image.Resampling.BILINEAR), dtype=np.float64) / 255
    value = np.asarray(frame)
    if value.ndim != 3 or value.shape[2] != 3 or not np.isfinite(value).all():
        raise SemanticError("Expected a finite H x W x 3 RGB image")
    if value.dtype != np.uint8:
        if value.min() < 0 or value.max() > 255:
            raise SemanticError("RGB values must be in [0,255]")
        value = value.astype(np.uint8)
    return _image_array(Image.fromarray(value))


def extract_features(frame, previous_frame=None) -> np.ndarray:
    """Pixels only: spatial color, edges, histogram and strictly past-frame changes."""
    rgb = _image_array(frame)
    gray = rgb.mean(axis=2)
    edge = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1])) + np.abs(np.diff(gray, axis=0, prepend=gray[:1]))
    pooled = rgb.reshape(6, 6, 8, 8, 3).mean(axis=(1, 3)).reshape(-1)
    edges = edge.reshape(6, 6, 8, 8).mean(axis=(1, 3)).reshape(-1)
    histogram = np.concatenate([np.histogram(rgb[:, :, c], bins=8, range=(0, 1))[0] / gray.size for c in range(3)])
    temporal = np.zeros(12)
    if previous_frame is not None:
        difference = np.abs(rgb - _image_array(previous_frame))
        temporal = difference.reshape(2, 18, 2, 32, 3).mean(axis=(1, 3)).reshape(-1)
    return np.concatenate([pooled, edges, histogram, temporal, [previous_frame is not None]])


def _softmax(values):
    shifted = values - values.max(axis=1, keepdims=True)
    values = np.exp(np.clip(shifted, -700, 0))
    return values / values.sum(axis=1, keepdims=True)


def _fit(features, labels, classes, regularization, seed):
    mean, scale = features.mean(axis=0), np.maximum(features.std(axis=0), .04)
    x = np.clip((features - mean) / scale, -6, 6)
    x = np.column_stack([x, np.ones(len(x))])
    target = np.eye(classes)[labels]
    weights = np.random.default_rng(seed).normal(0, .001, (x.shape[1], classes))
    m, v = np.zeros_like(weights), np.zeros_like(weights)
    for step in range(1, 301):
        gradient = x.T @ (_softmax(x @ weights) - target) / len(x)
        gradient[:-1] += regularization * weights[:-1]
        m, v = .9 * m + .1 * gradient, .999 * v + .001 * gradient ** 2
        weights -= .03 * (m / (1 - .9 ** step)) / (np.sqrt(v / (1 - .999 ** step)) + 1e-8)
    return mean, scale, weights


def _metrics(target, probabilities, names):
    if len(target) == 0:
        return {"n": 0, "accuracy": None, "log_loss": None, "brier": None, "macro_f1": None, "confusion_matrix": None}
    prediction = probabilities.argmax(axis=1)
    confusion = np.zeros((len(names), len(names)), dtype=int)
    for expected, actual in zip(target, prediction):
        confusion[expected, actual] += 1
    f1 = [2 * confusion[i, i] / max(1, confusion[i].sum() + confusion[:, i].sum())
          for i in range(len(names)) if confusion[i].sum()]
    return {"n": len(target), "accuracy": float((prediction == target).mean()),
            "log_loss": float(-np.log(np.clip(probabilities[np.arange(len(target)), target], 1e-12, 1)).mean()),
            "brier": float(((probabilities - np.eye(len(names))[target]) ** 2).sum(axis=1).mean()),
            "macro_f1": float(np.mean(f1)), "class_order": list(names), "confusion_matrix": confusion.tolist()}


def _guard_partition_inputs(records, split):
    ownership = {}
    for name, indices in split.items():
        for index in indices:
            row = records[index]
            for frame in (row["frame"], row.get("previous_frame")):
                if not frame:
                    continue
                digest = frame["sha256"]
                if digest in ownership and ownership[digest] != name:
                    raise SemanticError("Pixel input hash shared across train/validation/test partitions")
                ownership[digest] = name


def _split(records, seed, block_s, embargo_s, fixed_partitions=None):
    """Keep matches together; single-match experiments use separated source blocks."""
    matches = sorted({r["match_id"] for r in records})
    if fixed_partitions is not None:
        _object(fixed_partitions, {"train", "validation", "test"})
        assigned = []
        for name, groups in fixed_partitions.items():
            if not isinstance(groups, list) or not groups or any(not isinstance(group, str) for group in groups):
                raise SemanticError(f"{name}: fixed partitions require nonempty match ID lists")
            assigned.extend(groups)
        if len(assigned) != len(set(assigned)) or set(assigned) != set(matches):
            raise SemanticError("Fixed partitions must assign every eligible match exactly once")
        split = {name: [i for i, record in enumerate(records)
                 if record["match_id"] in groups] for name, groups in fixed_partitions.items()}
        _guard_partition_inputs(records, split)
        return "match_holdout_fixed", split, []
    mode = "match_holdout" if len(matches) >= 3 else "temporal_block_holdout"
    groups = matches if mode == "match_holdout" else sorted({
        f'{r["match_id"]}|{r["source_sha256"]}|{int(r["timestamp_s"] // block_s)}' for r in records})
    if len(groups) < 3:
        return mode, {key: [] for key in ("train", "validation", "test")}, []
    permutation = np.random.default_rng(seed).permutation(len(groups))
    test_n, validation_n = max(1, len(groups) // 5), max(1, len(groups) // 5)
    partitions = {"test": {groups[i] for i in permutation[:test_n]},
                  "validation": {groups[i] for i in permutation[test_n:test_n + validation_n]},
                  "train": {groups[i] for i in permutation[test_n + validation_n:]}}
    split, excluded = {key: [] for key in partitions}, []
    for index, row in enumerate(records):
        timestamp = row["timestamp_s"]
        group = row["match_id"] if mode == "match_holdout" else f'{row["match_id"]}|{row["source_sha256"]}|{int(timestamp // block_s)}'
        previous = row.get("previous_frame")
        if mode == "temporal_block_holdout" and (timestamp % block_s < embargo_s or
                timestamp % block_s > block_s - embargo_s or
                (previous and int(previous["timestamp_s"] // block_s) != int(timestamp // block_s))):
            excluded.append(row["sample_id"])
            continue
        for name, selected in partitions.items():
            if group in selected:
                split[name].append(index)
    # Protect current/current, current/previous and previous/previous inputs for
    # every split mode. IDs and claimed timestamps cannot bypass byte ownership.
    _guard_partition_inputs(records, split)
    return mode, split, excluded


class SemanticDetector:
    """Portable numerical checkpoint; model inputs never contain source IDs/labels."""
    def __init__(self, metadata, arrays):
        self.metadata = metadata
        self.arrays = arrays

    @classmethod
    def load(cls, path: str | Path):
        path = Path(path)
        if path.is_dir():
            path = path / "model.npz"
        metadata_path = path.with_suffix(".json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        _object(metadata, {"schema_version", "feature_version", "scope", "supervision", "model_sha256",
                           "dataset_sha256", "temperature", "confidence_threshold", "ood_distance_threshold",
                           "trained_states", "trained_events", "learned_samples", "split_mode"}, {"event_max_gap_s"})
        if metadata.get("schema_version") != 1 or metadata.get("feature_version") != FEATURE_VERSION:
            raise SemanticError("Unsupported semantic model schema/features")
        if metadata.get("model_sha256") != sha256(path.read_bytes()).hexdigest():
            raise SemanticError("Semantic checkpoint hash mismatch")
        with np.load(path, allow_pickle=False) as archive:
            arrays = {key: archive[key].copy() for key in archive.files}
        feature_n = len(extract_features(np.zeros((36, 64, 3), dtype=np.uint8)))
        expected = {"mean", "scale", "state_weights", "prototypes", "event_weights", "event_mean", "event_scale"}
        if set(arrays) != expected or any(not np.isfinite(value).all() for value in arrays.values()):
            raise SemanticError("Invalid numerical checkpoint")
        if (arrays["mean"].shape != (feature_n,) or arrays["scale"].shape != (feature_n,) or
                np.any(arrays["scale"] <= 0) or arrays["state_weights"].shape != (feature_n + 1, len(STATES)) or
                arrays["prototypes"].ndim != 2 or arrays["prototypes"].shape[1] != feature_n or
                not len(arrays["prototypes"]) or arrays["event_weights"].shape not in {(0,), (feature_n + 1, len(EVENTS))} or
                arrays["event_mean"].shape != (feature_n,) or arrays["event_scale"].shape != (feature_n,) or
                np.any(arrays["event_scale"] <= 0)):
            raise SemanticError("Invalid checkpoint dimensions")
        if metadata.get("scope") not in {"observer_truth", "player_observation"}:
            raise SemanticError("Invalid model visibility scope")
        if metadata["supervision"] not in {"ai_assisted_exploratory", "human_reviewed"}:
            raise SemanticError("Invalid supervision designation")
        _hash(metadata["dataset_sha256"])
        for key, choices in (("trained_states", STATES), ("trained_events", EVENTS)):
            value = metadata[key]
            if not isinstance(value, list) or any(item not in choices for item in value) or len(value) != len(set(value)):
                raise SemanticError("Invalid trained class designation")
        if len(metadata["trained_states"]) < 2 or bool(metadata["trained_events"]) != bool(arrays["event_weights"].size):
            raise SemanticError("Trained classes disagree with the checkpoint heads")
        if type(metadata["learned_samples"]) is not int or metadata["learned_samples"] < 2:
            raise SemanticError("Invalid learned sample count")
        if metadata["split_mode"] not in {"match_holdout", "match_holdout_fixed", "temporal_block_holdout"}:
            raise SemanticError("Invalid split mode")
        if arrays["event_weights"].size:
            maximum_gap = _number(metadata.get("event_max_gap_s"), "event_max_gap_s")
            if not 0 < maximum_gap <= 10:
                raise SemanticError("Event head requires a positive training frame-gap limit")
        for key in ("temperature", "ood_distance_threshold", "confidence_threshold"):
            value = _number(metadata.get(key), key)
            if value <= 0 or (key == "confidence_threshold" and value > 1):
                raise SemanticError("Invalid model threshold")
        return cls(metadata, arrays)

    def _distribution(self, features, weights, *, event=False):
        prefix = "event_" if event else ""
        x = np.clip((features - self.arrays[prefix + "mean"]) / self.arrays[prefix + "scale"], -6, 6)
        temperature = 1 if event else self.metadata["temperature"]
        return _softmax(np.column_stack([x, np.ones(len(x))]) @ weights / temperature)

    def predict(self, frame, previous_frame=None, *, previous_gap_s: float | None = None) -> dict:
        # Scene recognition sees the current image only. Adding a temporal event
        # head cannot silently shift the scene classifier's feature distribution.
        features = extract_features(frame)[None, :]
        probabilities = self._distribution(features, self.arrays["state_weights"])[0]
        normalized = np.clip((features[0] - self.arrays["mean"]) / self.arrays["scale"], -6, 6)
        distance = float(np.sqrt(((self.arrays["prototypes"] - normalized) ** 2).mean(axis=1)).min())
        confidence = float(probabilities.max())
        reason = ("out_of_distribution" if distance > self.metadata["ood_distance_threshold"] else
                  "low_class_confidence" if confidence < self.metadata["confidence_threshold"] else None)
        result = {"state": "unknown" if reason else STATES[int(probabilities.argmax())],
                  "suggested_state": STATES[int(probabilities.argmax())], "confidence": confidence,
                  "probabilities": dict(zip(STATES, map(float, probabilities))),
                  "score_definition": "uncalibrated_model_class_distribution", "abstained": reason is not None,
                  "abstention_reason": reason, "ood_distance": distance,
                  "visibility_scope": self.metadata["scope"], "supervision": self.metadata["supervision"],
                  "event": "unknown", "tactical_action": None, "move_classification": "unknown", "move_score": None}
        gap_valid = (previous_gap_s is not None and not isinstance(previous_gap_s, bool) and
                     isinstance(previous_gap_s, (int, float)) and isfinite(previous_gap_s) and
                     0 < previous_gap_s <= self.metadata.get("event_max_gap_s", 0) + 1e-9)
        result["event_abstention_reason"] = ("no_event_head" if not self.arrays["event_weights"].size else
            "missing_previous_frame" if previous_frame is None else
            "missing_or_unsupported_frame_gap" if not gap_valid else "scene_not_gameplay_pov" if result["state"] != "gameplay_pov" else
            "scene_abstained" if reason is not None else None)
        if (self.arrays["event_weights"].size and previous_frame is not None and reason is None
                and result["state"] == "gameplay_pov" and gap_valid):
            event_features = extract_features(frame, previous_frame)[None, :]
            event_probabilities = self._distribution(event_features, self.arrays["event_weights"], event=True)[0]
            result["event_probabilities"] = dict(zip(EVENTS, map(float, event_probabilities)))
            result["event_confidence"] = float(event_probabilities.max())
            if event_probabilities.max() >= self.metadata["confidence_threshold"]:
                result["event"] = EVENTS[int(event_probabilities.argmax())]
            else:
                result["event_abstention_reason"] = "low_event_class_confidence"
        return result


def train_semantic_detector(dataset: SemanticDataset | str | Path, out: str | Path, *,
                            allow_ai_labels: bool = False, seed: int = 42, scope: str = "observer_truth",
                            block_s: float = 600, embargo_s: float = 15,
                            partitions: dict[str, list[str]] | None = None,
                            progress: Callable[[dict], None] | None = None) -> dict:
    """Fit and evaluate a CPU softmax classifier without sharing match/source frames.

    AI labels are excluded by default. One/two-match block experiments are useful
    debugging evidence only, even if the held-out accuracy happens to be high.
    """
    # Revalidate bytes even when callers used verify_files=False for browsing.
    dataset = load_semantic_dataset(dataset.source_path if isinstance(dataset, SemanticDataset) else dataset)
    if type(seed) is not int or not isinstance(allow_ai_labels, bool):
        raise SemanticError("seed must be an integer and allow_ai_labels a boolean")
    if scope not in {"observer_truth", "player_observation"}:
        raise SemanticError("Choose an explicit visibility scope")
    block_s, embargo_s = _number(block_s, "block_s"), _number(embargo_s, "embargo_s")
    if block_s <= 30 or embargo_s < 10 or block_s <= 2 * embargo_s:
        raise SemanticError("Blocks must exceed 30s and contain a >=10s temporal embargo")
    accepted = [r for r in dataset.records if r["visibility_scope"] == scope and
                (r["verification"]["status"] == "human_verified" or
                 (allow_ai_labels and r["verification"]["status"] == "ai_inspected"))]
    supervision = "ai_assisted_exploratory" if any(r["verification"]["status"] == "ai_inspected" for r in accepted) else "human_reviewed"
    mode, split, excluded = _split(accepted, seed, block_s, embargo_s, partitions)
    report = {"schema_version": 1, "status": "collection_review_pending", "audit": dataset.audit(),
              "scope": scope, "supervision": supervision, "eligible_samples": len(accepted),
              "learned_samples": 0, "split": {"mode": mode, "seed": seed, "block_s": block_s,
                  "embargo_s": embargo_s, "excluded_sample_ids": excluded,
                  "partitions": {name: [accepted[i]["sample_id"] for i in indices] for name, indices in split.items()},
                  "matches": {name: sorted({accepted[i]["match_id"] for i in indices}) for name, indices in split.items()}},
              "test": None, "event_test": None, "validated_tactical_decisions": False,
              "limitations": ["Broadcast image classes do not establish tactical action or move quality.",
                  "Class distributions are model scores; no win-probability or calibration claim.",
                  "Temporal block holdouts do not establish generalization to another match.",
                  "AI-inspected labels are not independent human validation."]}
    report["split"]["class_counts"] = {name: {state: sum(accepted[i]["state"] == state for i in indices)
                                                for state in STATES} for name, indices in split.items()}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "model.npz").exists():
        raise SemanticError("Use a new experiment directory; an existing model cannot be overwritten")
    if not all(split.values()) or len({accepted[i]["state"] for i in split["train"]}) < 2:
        report["reason"] = "Need nonempty train/validation/test groups and at least two training classes."
        _write_report(out, report)
        return report
    if progress:
        progress({"stage": "features", "samples": len(accepted)})
    event_features = np.array([extract_features(dataset.base / r["frame"]["path"],
                         dataset.base / r["previous_frame"]["path"] if r.get("previous_frame") else None) for r in accepted])
    features = event_features.copy()
    features[:, -13:] = 0
    targets = np.array([STATES.index(r["state"]) for r in accepted])
    train, validation, test = (np.array(split[name]) for name in ("train", "validation", "test"))
    candidates = []
    for l2 in (.01, .1, 1):
        mean, scale, weights = _fit(features[train], targets[train], len(STATES), l2, seed)
        x = np.clip((features[validation] - mean) / scale, -6, 6)
        logits = np.column_stack([x, np.ones(len(x))]) @ weights
        for temperature in (.5, 1, 2):
            metric = _metrics(targets[validation], _softmax(logits / temperature), STATES)
            candidates.append((metric["log_loss"], l2, temperature, metric))
    _, l2, temperature, validation_metrics = min(candidates, key=lambda item: (item[0], item[1], item[2]))
    refit = np.concatenate([train, validation])
    mean, scale, weights = _fit(features[refit], targets[refit], len(STATES), l2, seed)
    prototype_indices = (np.random.default_rng(seed).choice(len(refit), 2048, replace=False)
                         if len(refit) > 2048 else np.arange(len(refit)))
    prototypes = np.clip((features[refit[prototype_indices]] - mean) / scale, -6, 6)
    # Distance gate is determined from fit data only. It is not tuned on test.
    if len(prototypes) > 1:
        nearest = []
        # Blocks keep the auxiliary OOD calculation bounded for large corpora.
        norms = (prototypes ** 2).sum(axis=1)
        for start in range(0, len(prototypes), 128):
            block = prototypes[start:start + 128]
            squared = (block ** 2).sum(axis=1)[:, None] + norms[None, :] - 2 * block @ prototypes.T
            squared[np.arange(len(block)), np.arange(start, start + len(block))] = np.inf
            nearest.extend(np.sqrt(np.maximum(squared.min(axis=1), 0) / features.shape[1]))
        threshold = max(.5, float(np.quantile(nearest, .95)) * 2)
    else:
        threshold = .5
    event_weights, e_mean, e_scale = np.array([]), mean.copy(), scale.copy()
    event_refit = [i for i in refit if accepted[i].get("event_label") not in {None, "unknown"} and accepted[i].get("previous_frame")]
    event_test = [i for i in test if accepted[i].get("event_label") not in {None, "unknown"} and accepted[i].get("previous_frame")]
    if len(event_refit) >= 10 and len({accepted[i]["event_label"] for i in event_refit}) >= 2:
        event_target = np.array([EVENTS.index(accepted[i]["event_label"]) for i in event_refit])
        e_mean, e_scale, e_weights = _fit(event_features[event_refit], event_target, len(EVENTS), l2, seed)
        event_weights = e_weights
    arrays = {"mean": mean, "scale": scale, "state_weights": weights,
              "prototypes": prototypes, "event_weights": event_weights, "event_mean": e_mean, "event_scale": e_scale}
    checkpoint = out / "model.npz"
    np.savez_compressed(checkpoint, **arrays)
    metadata = {"schema_version": 1, "feature_version": FEATURE_VERSION, "scope": scope,
                "supervision": supervision, "model_sha256": sha256(checkpoint.read_bytes()).hexdigest(),
                "dataset_sha256": dataset.sha256, "temperature": temperature,
                "confidence_threshold": .55, "ood_distance_threshold": threshold,
                "trained_states": sorted({accepted[i]["state"] for i in refit}),
                "trained_events": sorted({accepted[i]["event_label"] for i in event_refit}) if event_weights.size else [],
                "learned_samples": len(refit), "split_mode": mode}
    if event_weights.size:
        metadata["event_max_gap_s"] = max(accepted[i]["timestamp_s"] - accepted[i]["previous_frame"]["timestamp_s"] for i in event_refit)
    (out / "model.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    detector = SemanticDetector.load(checkpoint)
    probabilities = detector._distribution(features[test], weights)
    metrics = _metrics(targets[test], probabilities, STATES)
    counts = np.bincount(targets[refit], minlength=len(STATES)) + 1
    baseline = np.broadcast_to(counts / counts.sum(), (len(test), len(STATES)))
    selected, abstained = [], 0
    for index in test:
        record = accepted[index]
        prediction = detector.predict(dataset.base / record["frame"]["path"],
                                      dataset.base / record["previous_frame"]["path"] if record.get("previous_frame") else None,
                                      previous_gap_s=record["timestamp_s"] - record["previous_frame"]["timestamp_s"] if record.get("previous_frame") else None)
        abstained += int(prediction["abstained"])
        selected.append({"sample_id": record["sample_id"], "expected_state": record["state"], **prediction})
    metrics["abstention_rate"] = abstained / len(test)
    metrics["accepted_n"] = len(test) - abstained
    metrics["accepted_accuracy"] = (sum(r["state"] == r["expected_state"] for r in selected if not r["abstained"]) /
                                      (len(test) - abstained)) if abstained < len(test) else None
    if event_weights.size and event_test:
        event_target = np.array([EVENTS.index(accepted[i]["event_label"]) for i in event_test])
        report["event_test"] = _metrics(event_target, detector._distribution(event_features[event_test], event_weights, event=True), EVENTS)
        report["event_test"]["abstention_applied"] = False
        report["event_test"]["evaluation_definition"] = "raw_head_argmax_on_labeled_temporal_samples"
        report["event_test"]["unseen_training_events"] = sorted({accepted[i]["event_label"] for i in event_test} - set(metadata["trained_events"]))
        event_predictions = []
        for index in event_test:
            row = accepted[index]
            prediction = detector.predict(dataset.base / row["frame"]["path"], dataset.base / row["previous_frame"]["path"],
                                          previous_gap_s=row["timestamp_s"] - row["previous_frame"]["timestamp_s"])
            event_predictions.append({"sample_id": row["sample_id"], "expected_event": row["event_label"],
                                      "event": prediction["event"], "abstention_reason": prediction["event_abstention_reason"]})
        accepted_events = [item for item in event_predictions if item["event"] != "unknown"]
        report["event_test"]["gated_inference"] = {"accepted_n": len(accepted_events),
            "abstention_rate": 1 - len(accepted_events) / len(event_test),
            "accepted_accuracy": sum(item["event"] == item["expected_event"] for item in accepted_events) / len(accepted_events) if accepted_events else None,
            "predictions": event_predictions}
    report.update({"status": "trained_exploratory" if supervision != "human_reviewed" or mode not in {"match_holdout", "match_holdout_fixed"} else "trained_human_reviewed",
                   "learned_samples": len(refit), "selection": {"regularization": l2, "temperature": temperature,
                   "validation_metrics": validation_metrics, "test_used_for_selection": False},
                   "test": {"metrics": metrics, "global_frequency_baseline": _metrics(targets[test], baseline, STATES),
                            "predictions": selected}, "model_sha256": metadata["model_sha256"]})
    report["trained_states"] = metadata["trained_states"]
    report["trained_events"] = metadata["trained_events"]
    report["test"]["unseen_training_states"] = sorted(set(accepted[i]["state"] for i in test) - set(metadata["trained_states"]))
    report["test"]["independent_matches"] = len(report["split"]["matches"]["test"])
    report["test"]["frame_metrics_assume_independent_observations"] = False
    _write_report(out, report)
    if progress:
        progress({"stage": "complete", "status": report["status"], "learned_samples": len(refit)})
    return report


def _write_report(out, report):
    (out / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    metrics = report["test"]["metrics"] if report["test"] else None
    text = ("# Detector semântico visual\n\n"
            f"Status: {report['status']}. Supervisão: {report['supervision']}.\n\n"
            f"Amostras elegíveis: {report['eligible_samples']}; aprendidas: {report['learned_samples']}. "
            f"Split: {report['split']['mode']}.\n\n"
            f"Teste: {json.dumps(metrics, ensure_ascii=False)}.\n\n"
            "Reconhece classes visuais de transmissão. Não estabelece decisão tática, "
            "qualidade de lance nem probabilidade de vitória. Rótulos inspecionados por IA "
            "não equivalem a revisão humana independente. Holdout de blocos de uma VOD "
            "não mede generalização entre partidas. Mídias permanecem locais.\n")
    (out / "MODEL_CARD.md").write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-ai-labels", action="store_true")
    parser.add_argument("--scope", choices=("observer_truth", "player_observation"), default="observer_truth")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--block-s", type=float, default=600)
    parser.add_argument("--embargo-s", type=float, default=15)
    args = parser.parse_args(argv)
    report = train_semantic_detector(args.dataset, args.out, allow_ai_labels=args.allow_ai_labels,
                                    scope=args.scope, seed=args.seed, block_s=args.block_s, embargo_s=args.embargo_s)
    print(json.dumps({key: report[key] for key in ("status", "eligible_samples", "learned_samples", "supervision")}, indent=2))


if __name__ == "__main__":
    main()
