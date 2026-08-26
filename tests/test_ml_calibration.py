import numpy as np

from app.ml.models import ModelTrainer


def test_logistic_training_records_calibration_metrics():
    X_train = np.array([[0.0], [1.0], [0.2], [0.8], [0.1], [0.9]], dtype=np.float32)
    y_train = np.array([0, 1, 0, 1, 0, 1], dtype=np.int32)
    X_test = np.array([[0.3], [0.7], [0.4], [0.6]], dtype=np.float32)
    y_test = np.array([0, 1, 0, 1], dtype=np.int32)
    trainer = ModelTrainer("TESTUSDT", "logistic", "1h")
    metrics = trainer.fit(X_train, y_train, X_test, y_test)
    assert 0.0 <= metrics["test_brier"] <= 1.0
    assert 0.0 <= metrics["test_ece"] <= 1.0
