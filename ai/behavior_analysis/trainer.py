"""
Module 6 — XGBoost Behavioral Model Trainer
===========================================
Bootstraps empirical retail session feature distributions, trains a multi-class
XGBoost classifier, evaluates accuracy with Scikit-learn, and exports the model.
"""

import logging
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

from ai.behavior_analysis.xgb_classifier import (
    ARCHETYPE_MAP,
    FEATURE_NAMES,
    REVERSE_ARCHETYPE_MAP,
)
from ai.behavior_analysis.models import ShopperArchetype

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xgb_trainer")


def generate_synthetic_training_data(
    samples_per_class: int = 400,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate realistic synthetic feature vectors for the 5 archetypes
    using calibrated retail empirical priors.
    """
    np.random.seed(seed)
    x_list = []
    y_list = []

    for archetype, label_idx in REVERSE_ARCHETYPE_MAP.items():
        n = samples_per_class

        if archetype == ShopperArchetype.BRAND_LOYAL:
            # Brand concentration >= 0.75, low gaze alternation (0-1.0), promo = 0
            pe = np.random.uniform(0.4, 0.85, n)
            dtr = np.random.uniform(0.2, 2.0, n)
            zb = np.random.randint(1, 3, n)
            gar = np.random.uniform(0.0, 1.0, n)
            prr = np.random.uniform(1.2, 5.0, n)
            bc = np.random.uniform(0.76, 1.0, n)
            pdc = np.full(n, 0)

        elif archetype == ShopperArchetype.COMPARISON_SHOPPER:
            # Gaze alternation >= 2.0, pickup to return ratio <= 0.95, moderate brand conc
            pe = np.random.uniform(0.3, 0.65, n)
            dtr = np.random.uniform(0.4, 3.0, n)
            zb = np.random.randint(1, 4, n)
            gar = np.random.uniform(2.0, 10.0, n)
            prr = np.random.uniform(0.1, 0.9, n)
            bc = np.random.uniform(0.2, 0.65, n)
            pdc = np.random.randint(0, 2, n)

        elif archetype == ShopperArchetype.IMPULSE_BUYER:
            # Promo deviations >= 1, gaze alternation < 2.0, brand conc < 0.75
            pe = np.random.uniform(0.3, 0.65, n)
            dtr = np.random.uniform(0.3, 1.5, n)
            zb = np.random.randint(1, 4, n)
            gar = np.random.uniform(0.0, 1.8, n)
            prr = np.random.uniform(1.0, 3.0, n)
            bc = np.random.uniform(0.2, 0.65, n)
            pdc = np.random.randint(1, 6, n)

        elif archetype == ShopperArchetype.QUICK_BUYER:
            # High path efficiency (>= 0.65), low zones (1-2), low dwell (<= 0.3), promo = 0
            pe = np.random.uniform(0.68, 0.98, n)
            dtr = np.random.uniform(0.05, 0.28, n)
            zb = np.random.randint(1, 3, n)
            gar = np.random.uniform(0.0, 1.5, n)
            prr = np.random.uniform(1.2, 4.0, n)
            bc = np.random.uniform(0.3, 0.70, n)
            pdc = np.full(n, 0)

        elif archetype == ShopperArchetype.EXPLORER:
            # Low path efficiency (<= 0.4), high zone breadth (>= 3), promo = 0
            pe = np.random.uniform(0.05, 0.38, n)
            dtr = np.random.uniform(0.4, 3.0, n)
            zb = np.random.randint(3, 8, n)
            gar = np.random.uniform(0.0, 1.8, n)
            prr = np.random.uniform(0.2, 1.5, n)
            bc = np.random.uniform(0.1, 0.55, n)
            pdc = np.full(n, 0)


        # Add Gaussian noise for natural overlap
        pe = np.clip(pe + np.random.normal(0, 0.03, n), 0.0, 1.0)
        bc = np.clip(bc + np.random.normal(0, 0.03, n), 0.0, 1.0)

        features = np.column_stack([pe, dtr, zb, gar, prr, bc, pdc])
        x_list.append(features)
        y_list.append(np.full(n, label_idx))

    x = np.vstack(x_list)
    y = np.concatenate(y_list)
    return x, y


def train_and_save_model(
    output_dir: Optional[Path] = None,
    samples_per_class: int = 500,
) -> Dict[str, float]:
    """Train the XGBoost behavioral model and save to disk."""
    import xgboost as xgb
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split

    out_dir = output_dir or Path(__file__).parent / "models"
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "xgb_shopper_model.json"

    logger.info("Generating calibrated training distribution...")
    x, y = generate_synthetic_training_data(samples_per_class=samples_per_class)

    x_train, x_val, y_train, y_val = train_test_split(
        x, y, test_size=0.25, random_state=42, stratify=y
    )

    logger.info(f"Training XGBoost classifier on {len(x_train)} samples...")
    classifier = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="multi:softprob",
        num_class=5,
        random_state=42,
        eval_metric="mlogloss",
    )

    classifier.fit(
        x_train,
        y_train,
        eval_set=[(x_val, y_val)],
        verbose=False,
    )

    y_pred = classifier.predict(x_val)
    acc = float(accuracy_score(y_val, y_pred))
    f1 = float(f1_score(y_val, y_pred, average="weighted"))

    logger.info(f"Validation Accuracy: {acc * 100:.2f}% | F1-Score: {f1 * 100:.2f}%")

    classifier.save_model(str(model_path))
    logger.info(f"Model successfully exported to {model_path}")

    return {
        "accuracy": acc,
        "f1_score": f1,
        "samples_trained": len(x_train),
        "model_path": str(model_path),
    }


if __name__ == "__main__":
    train_and_save_model()
