# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Train Arjuna using the cleaned, balanced dataset from data/ml/arjuna_final_dataset.json.
Saves metrics and model metadata.
"""

import os
import json
import pickle
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import Counter
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, f1_score

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
DATA_DIR = PROJECT_ROOT / "data" / "ml"
MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Load dataset
# ----------------------------------------------------------------------
dataset_path = DATA_DIR / "arjuna_final_dataset.json"
if not dataset_path.exists():
    print(f"Dataset not found at {dataset_path}. Run build_arjuna_dataset.py first.")
    exit(1)

with open(dataset_path, "r") as f:
    data = json.load(f)

texts = [item["text"] for item in data]
labels = [item["label"] for item in data]

print(f"Loaded {len(texts)} samples.")
label_counts = Counter(labels)
print("Class distribution:")
for k, v in label_counts.items():
    print(f"  {k}: {v}")

# Check that all target classes are present
target_classes = {"benign", "prompt_injection", "policy_bypass", "data_exfiltration"}
missing = target_classes - set(label_counts.keys())
if missing:
    print(f"❌ Missing classes: {missing}. Aborting training.")
    exit(1)

# ----------------------------------------------------------------------
# Feature extraction
# ----------------------------------------------------------------------
label_map = {l: i for i, l in enumerate(sorted(set(labels)))}
y = np.array([label_map[l] for l in labels])

vectorizer = TfidfVectorizer(max_features=2000, ngram_range=(1, 3),
                              stop_words="english", sublinear_tf=True, use_idf=True)
X = vectorizer.fit_transform(texts)

# ----------------------------------------------------------------------
# Train/test split
# ----------------------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ----------------------------------------------------------------------
# Grid search for Logistic Regression (main model)
# ----------------------------------------------------------------------
print("\nTraining Logistic Regression (main model)...")
param_grid = {
    'C': [0.5, 1.0, 5.0, 10.0],
    'solver': ['lbfgs', 'newton-cg', 'saga'],
    'class_weight': ['balanced', None]
}
grid = GridSearchCV(LogisticRegression(max_iter=20000, random_state=42),
                    param_grid, cv=3, scoring='f1_macro', n_jobs=-1)
grid.fit(X_train, y_train)
best_lr = grid.best_estimator_
print(f"Best params: {grid.best_params_}")
print(f"Cross-val macro F1: {grid.best_score_:.4f}")

y_pred_lr = best_lr.predict(X_test)
lr_f1 = f1_score(y_test, y_pred_lr, average='macro')
print(f"Test macro F1: {lr_f1:.4f}")

# ----------------------------------------------------------------------
# Optional benchmark: Linear SVM (uncomment to run)
# ----------------------------------------------------------------------
# print("\nTraining Linear SVM (benchmark)...")
# svm = LinearSVC(random_state=42, dual='auto', max_iter=20000)
# svm_param_grid = {
#     'C': [0.5, 1.0, 5.0, 10.0],
#     'class_weight': ['balanced', None]
# }
# svm_grid = GridSearchCV(svm, svm_param_grid, cv=3, scoring='f1_macro', n_jobs=-1)
# svm_grid.fit(X_train, y_train)
# best_svm = svm_grid.best_estimator_
# print(f"Best params: {svm_grid.best_params_}")
# print(f"Cross-val macro F1: {svm_grid.best_score_:.4f}")
# y_pred_svm = best_svm.predict(X_test)
# svm_f1 = f1_score(y_test, y_pred_svm, average='macro')
# print(f"Test macro F1: {svm_f1:.4f}")
#
# if svm_f1 > lr_f1:
#     print(f"Linear SVM performs better; using it as final model.")
#     best_model = best_svm
# else:
#     best_model = best_lr
#     print("Logistic Regression remains final model.")

best_model = best_lr   # keep LR as main; SVM can be used for comparison

# ----------------------------------------------------------------------
# Evaluation report
# ----------------------------------------------------------------------
id_to_label = {i: l for l, i in label_map.items()}
target_names = [id_to_label[i] for i in range(len(id_to_label))]
report = classification_report(y_test, y_pred_lr, target_names=target_names, output_dict=True)

# Save metrics
metrics = {
    "timestamp": datetime.now().isoformat(),
    "dataset_size": len(texts),
    "class_distribution": dict(label_counts),
    "best_params": grid.best_params_,
    "cross_val_score": grid.best_score_,
    "test_macro_f1": lr_f1,
    "classification_report": report
}
metrics_path = MODEL_DIR / "arjuna_training_metrics.json"
with open(metrics_path, "w") as f:
    json.dump(metrics, f, indent=2)
print(f"Metrics saved to {metrics_path}")

print("\nClassification Report:")
print(classification_report(y_test, y_pred_lr, target_names=target_names))

# ----------------------------------------------------------------------
# Save model files
# ----------------------------------------------------------------------
model_path = MODEL_DIR / "arjuna_model.pkl"
vectorizer_path = MODEL_DIR / "arjuna_vectorizer.pkl"
label_map_path = MODEL_DIR / "arjuna_label_map.json"

with open(model_path, "wb") as f:
    pickle.dump(best_model, f)
with open(vectorizer_path, "wb") as f:
    pickle.dump(vectorizer, f)
with open(label_map_path, "w") as f:
    json.dump(label_map, f, indent=2)

# Copy to Arjuna engine folder
arjuna_dir = PROJECT_ROOT / "src" / "engines" / "arjuna"
arjuna_dir.mkdir(parents=True, exist_ok=True)
for fname in ["arjuna_model.pkl", "arjuna_vectorizer.pkl", "arjuna_label_map.json"]:
    src = MODEL_DIR / fname
    dst = arjuna_dir / fname
    if src.exists():
        import shutil
        shutil.copy(src, dst)
        print(f"Copied {fname} to {dst}")

print("\n✅ Arjuna retrained with cleaned dataset. Restart server and test.")
