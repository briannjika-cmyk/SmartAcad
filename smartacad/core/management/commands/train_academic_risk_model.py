import csv
import hashlib
from io import StringIO
import json
import math
from collections import Counter
from pathlib import Path

import joblib
from django.core.management.base import BaseCommand, CommandError
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    f1_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from core.academic_risk import (
    DIFFICULTY_FEATURES,
    FEATURES,
    HIGH_RISK_THRESHOLD,
    HABIT_FEATURES,
    MODEL_DIRECTORY,
    MODEL_PATH,
    NUMERIC_FEATURES,
    classify_risk,
)


TARGET_COLUMN = "academic_risk"
ID_COLUMN = "student_id"
LABELS = ("Low", "Medium", "High")
MINIMUM_ROWS = 100
MINIMUM_CLASS_SIZE = 10


class Command(BaseCommand):
    help = (
        "Validate, evaluate, and train the academic-risk classifier "
        "from an anonymized CSV dataset."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            required=True,
            help="Path to the anonymized training CSV.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"]).expanduser()
        if not csv_path.is_file():
            raise CommandError(f"Training CSV does not exist: {csv_path}")

        try:
            raw_bytes = csv_path.read_bytes()
            rows = list(
                csv.DictReader(
                    StringIO(raw_bytes.decode("utf-8-sig"))
                )
            )
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            raise CommandError(f"Could not read training CSV: {exc}") from exc

        if not rows:
            raise CommandError("Training CSV contains no data rows.")

        missing_columns = (
            {ID_COLUMN, TARGET_COLUMN, *FEATURES}
            - set(rows[0].keys())
        )
        if missing_columns:
            raise CommandError(
                "Training CSV is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )
        if len(rows) < MINIMUM_ROWS:
            raise CommandError(
                f"At least {MINIMUM_ROWS} student records are required; "
                f"found {len(rows)}."
            )

        student_ids = [row[ID_COLUMN].strip() for row in rows]
        if any(not student_id for student_id in student_ids):
            raise CommandError("Every row must have a non-empty student_id.")
        if len(set(student_ids)) != len(student_ids):
            raise CommandError(
                "Each student_id must occur only once so records from the "
                "same student cannot leak across validation folds."
            )

        features = []
        labels = []
        for row_number, row in enumerate(rows, start=2):
            label = row[TARGET_COLUMN].strip()
            if label not in LABELS:
                raise CommandError(
                    f"Row {row_number} has an unsupported academic_risk "
                    f"label: {label!r}. Expected Low, Medium, or High."
                )
            features.append(
                self._parse_features(row, row_number)
            )
            labels.append(label)

        label_counts = Counter(labels)
        insufficient = {
            label: count
            for label, count in label_counts.items()
            if count < MINIMUM_CLASS_SIZE
        }
        missing_labels = set(LABELS) - set(label_counts)
        if missing_labels or insufficient:
            details = [
                f"{label}={label_counts.get(label, 0)}"
                for label in LABELS
            ]
            raise CommandError(
                "Training requires at least "
                f"{MINIMUM_CLASS_SIZE} examples per risk category and all "
                "three categories. Counts: " + ", ".join(details)
            )

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=4,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=1,
        )
        folds = min(5, min(label_counts.values()))
        cross_validator = StratifiedKFold(
            n_splits=folds,
            shuffle=True,
            random_state=42,
        )
        model_classes = sorted(LABELS)
        out_of_fold_probabilities = cross_val_predict(
            model,
            features,
            labels,
            cv=cross_validator,
            method="predict_proba",
        )
        out_of_fold_predictions = [
            classify_risk(
                dict(zip(model_classes, probabilities)),
                high_risk_threshold=HIGH_RISK_THRESHOLD,
            )
            for probabilities in out_of_fold_probabilities
        ]
        report = classification_report(
            labels,
            out_of_fold_predictions,
            labels=LABELS,
            output_dict=True,
            zero_division=0,
        )

        model.fit(features, labels)
        metadata = {
            "model_type": "RandomForestClassifier",
            "target": TARGET_COLUMN,
            "labels": list(LABELS),
            "features": list(FEATURES),
            "training_rows": len(rows),
            "class_counts": dict(label_counts),
            "decision_policy": {
                "high_risk_threshold": HIGH_RISK_THRESHOLD,
                "description": (
                    "Predict High when its model score meets the threshold; "
                    "otherwise choose the highest-scoring non-High category."
                ),
            },
            "validation": {
                "method": f"{folds}-fold stratified cross-validation",
                "threshold_note": (
                    "The High-risk threshold was selected after exploratory "
                    "evaluation on this dataset; these results are "
                    "preliminary and need independent validation."
                ),
                "accuracy": round(
                    accuracy_score(labels, out_of_fold_predictions), 4
                ),
                "balanced_accuracy": round(
                    balanced_accuracy_score(
                        labels,
                        out_of_fold_predictions,
                    ),
                    4,
                ),
                "macro_f1": round(
                    f1_score(
                        labels,
                        out_of_fold_predictions,
                        labels=LABELS,
                        average="macro",
                        zero_division=0,
                    ),
                    4,
                ),
                "per_class": {
                    label: {
                        "precision": round(report[label]["precision"], 4),
                        "recall": round(report[label]["recall"], 4),
                        "f1": round(report[label]["f1-score"], 4),
                        "support": report[label]["support"],
                    }
                    for label in LABELS
                },
            },
            "training_data_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        }

        MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)
        temporary_model_path = MODEL_PATH.with_suffix(".joblib.tmp")
        temporary_metadata_path = MODEL_PATH.with_suffix(".json.tmp")
        joblib.dump(model, temporary_model_path)
        temporary_metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )
        temporary_model_path.replace(MODEL_PATH)
        temporary_metadata_path.replace(MODEL_PATH.with_suffix(".json"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Trained model with {len(rows)} student records "
                f"({folds}-fold stratified validation)."
            )
        )
        self.stdout.write(
            "Validation: "
            f"accuracy={metadata['validation']['accuracy']:.3f}, "
            "balanced_accuracy="
            f"{metadata['validation']['balanced_accuracy']:.3f}, "
            f"macro_f1={metadata['validation']['macro_f1']:.3f}"
        )
        self.stdout.write(
            "Decision policy: "
            f"High-risk threshold="
            f"{metadata['decision_policy']['high_risk_threshold']:.2f}"
        )
        for label in LABELS:
            metrics = metadata["validation"]["per_class"][label]
            self.stdout.write(
                f"{label}: precision={metrics['precision']:.3f}, "
                f"recall={metrics['recall']:.3f}, "
                f"F1={metrics['f1']:.3f}, "
                f"support={metrics['support']}"
            )
        self.stdout.write(f"Model artifact: {MODEL_PATH}")
        self.stdout.write(
            self.style.WARNING(
                "The classifier predicts the supplied academic_risk "
                "categories. It is a screening aid, not a diagnosis or "
                "basis for automatic student decisions."
            )
        )

    def _parse_features(self, row, row_number):
        values = []
        bounds = {
            "attendance_percentage": (0, 100),
            "gpa": (0, 4),
            "study_hours_per_day": (0, 24),
            "assignment_completion_percentage": (0, 100),
        }
        for feature in NUMERIC_FEATURES:
            try:
                value = float(row[feature])
            except (TypeError, ValueError) as exc:
                raise CommandError(
                    f"Row {row_number} has invalid {feature}."
                ) from exc
            if not math.isfinite(value):
                raise CommandError(
                    f"Row {row_number} has non-finite {feature}."
                )
            minimum, maximum = bounds[feature]
            if not minimum <= value <= maximum:
                raise CommandError(
                    f"Row {row_number} has {feature} outside "
                    f"{minimum}..{maximum}."
                )
            values.append(value)

        for feature in (*DIFFICULTY_FEATURES, *HABIT_FEATURES):
            value = row[feature].strip()
            if value not in ("0", "1"):
                raise CommandError(
                    f"Row {row_number} has invalid binary feature "
                    f"{feature}; expected 0 or 1."
                )
            values.append(int(value))
        return values
