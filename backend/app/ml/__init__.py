"""
ml package — machine learning models, training pipelines, inference, and preprocessing.

Sub-packages:
- models/        — Serialized trained models (XGBoost, Scikit-learn, etc.)
- training/      — Training scripts and experiment tracking
- inference/     — Inference pipelines called by analytics services
- preprocessing/ — Feature engineering and data preparation utilities

NOTE: In this package, 'models' refers to trained AI/ML models,
NOT SQLAlchemy ORM entities (those live in each domain's domain/entities.py).
"""
