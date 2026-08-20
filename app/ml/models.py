"""
ML Model Training and Prediction
Trains classification models on prepared datasets
"""
import numpy as np
import os
import pickle
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_validate, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from app.ml.registry import approve_version, get_active, new_version, register_candidate, version_dir
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


MODEL_DIR = "/app/models"  # Inside container


def ensure_model_dir():
    """Create models directory if it doesn't exist"""
    os.makedirs(MODEL_DIR, exist_ok=True)


def get_model_path(model_name: str, symbol: str, timeframe: str = "1h") -> str:
    """Get path for model file"""
    return os.path.join(MODEL_DIR, f"{symbol}_{timeframe}_{model_name}.pkl")


def get_scaler_path(symbol: str, timeframe: str = "1h") -> str:
    """Get path for feature scaler"""
    return os.path.join(MODEL_DIR, f"{symbol}_{timeframe}_scaler.pkl")


class ModelTrainer:
    """Train and manage ML models"""
    
    def __init__(self, symbol: str, model_type: str = "rf", timeframe: str = "1h"):
        self.symbol = symbol
        self.model_type = model_type.lower()
        self.timeframe = timeframe
        self.model = None
        self.scaler = None
        self.metrics = {}
        
        # Initialize model
        if self.model_type == "logistic":
            self.model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
        elif self.model_type == "rf":
            self.model = RandomForestClassifier(n_estimators=300, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1)
        elif self.model_type == "xgboost":
            if not HAS_XGBOOST:
                raise ValueError("XGBoost not installed. Install with: pip install xgboost")
            self.model = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=-1)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def fit(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray = None, y_test: np.ndarray = None):
        """
        Train model with feature scaling
        
        Args:
            X_train: Training features (n_samples, n_features)
            y_train: Training labels (n_samples,)
            X_test: Test features (optional)
            y_test: Test labels (optional)
        
        Returns:
            metrics dict
        """
        # Feature scaling
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate on training set
        y_train_pred = self.model.predict(X_train_scaled)
        
        self.metrics = {
            "train_accuracy": float(accuracy_score(y_train, y_train_pred)),
            "train_precision": float(precision_score(y_train, y_train_pred, zero_division=0)),
            "train_recall": float(recall_score(y_train, y_train_pred, zero_division=0)),
            "train_f1": float(f1_score(y_train, y_train_pred, zero_division=0)),
        }
        
        # Get probability predictions for AUC
        if hasattr(self.model, 'predict_proba'):
            try:
                y_train_proba = self.model.predict_proba(X_train_scaled)[:, 1]
                self.metrics["train_auc"] = float(roc_auc_score(y_train, y_train_proba))
            except (IndexError, ValueError):
                # Only one class present in training data
                self.metrics["train_auc"] = None
        
        # Evaluate on test set if provided
        if X_test is not None and y_test is not None:
            X_test_scaled = self.scaler.transform(X_test)
            y_test_pred = self.model.predict(X_test_scaled)
            
            self.metrics.update({
                "test_accuracy": float(accuracy_score(y_test, y_test_pred)),
                "test_precision": float(precision_score(y_test, y_test_pred, zero_division=0)),
                "test_recall": float(recall_score(y_test, y_test_pred, zero_division=0)),
                "test_f1": float(f1_score(y_test, y_test_pred, zero_division=0)),
                "confusion_matrix": confusion_matrix(y_test, y_test_pred).tolist(),
            })
            
            if hasattr(self.model, 'predict_proba'):
                try:
                    y_test_proba = self.model.predict_proba(X_test_scaled)[:, 1]
                    self.metrics["test_auc"] = float(roc_auc_score(y_test, y_test_proba))
                except (IndexError, ValueError):
                    # Only one class present in test data
                    self.metrics["test_auc"] = None
        
        return self.metrics
    
    def cross_validate(self, X: np.ndarray, y: np.ndarray, cv: int = 5) -> Dict[str, Any]:
        """
        Perform k-fold cross validation
        
        Returns:
            cross validation metrics
        """
        if len(np.unique(y)) < 2:
            return {f"cv_{metric}_{suffix}": None for metric in ("accuracy", "precision", "recall", "f1", "roc_auc") for suffix in ("mean", "std")}

        splitter = TimeSeriesSplit(n_splits=cv)
        
        scoring = ['accuracy', 'precision', 'recall', 'f1']
        if hasattr(self.model, 'predict_proba'):
            scoring.append('roc_auc')
        
        # Scale features
        # Keep the production scaler fitted on all training data in fit().
        # CV uses an isolated scaler per fold through a pipeline in sklearn.
        from sklearn.pipeline import make_pipeline
        cv_model = make_pipeline(StandardScaler(), self._new_model())
        
        cv_results = cross_validate(cv_model, X, y, cv=splitter, scoring=scoring, error_score=np.nan)
        
        # Format results
        cv_metrics = {}
        for metric in scoring:
            key = f"test_{metric}"
            scores = cv_results[key]
            # Filter out inf/nan values
            valid_scores = scores[np.isfinite(scores)]
            if len(valid_scores) > 0:
                cv_metrics[f"cv_{metric}_mean"] = float(np.mean(valid_scores))
                cv_metrics[f"cv_{metric}_std"] = float(np.std(valid_scores))
            else:
                cv_metrics[f"cv_{metric}_mean"] = None
                cv_metrics[f"cv_{metric}_std"] = None
        
        return cv_metrics

    def _new_model(self):
        """Create a fresh estimator for time-series cross-validation."""
        if self.model_type == "logistic":
            return LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
        if self.model_type == "rf":
            return RandomForestClassifier(n_estimators=300, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1)
        return xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=-1)
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions
        
        Args:
            X: Features (n_samples, n_features)
        
        Returns:
            predictions (0/1), probabilities (0-1)
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Call fit() first.")
        
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        
        if hasattr(self.model, 'predict_proba'):
            probability_matrix = self.model.predict_proba(X_scaled)
            if probability_matrix.shape[1] == 1:
                trained_class = int(self.model.classes_[0])
                probabilities = probability_matrix[:, 0] if trained_class == 1 else np.zeros(len(predictions))
            else:
                probabilities = probability_matrix[:, 1]
        else:
            probabilities = predictions.astype(float)
        
        return predictions, probabilities
    
    def save(self):
        """Save model and scaler to disk"""
        ensure_model_dir()
        
        model_path = get_model_path(self.model_type, self.symbol, self.timeframe)
        scaler_path = get_scaler_path(self.symbol, self.timeframe)
        
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        return {
            "model_path": model_path,
            "scaler_path": scaler_path,
            "status": "saved"
        }

    def save_version(self, metrics: Dict[str, Any], dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Persist an immutable candidate and register its metadata."""
        version = new_version()
        directory = version_dir(self.symbol, self.timeframe, self.model_type, version)
        os.makedirs(directory, exist_ok=True)
        model_path = os.path.join(directory, "model.pkl")
        scaler_path = os.path.join(directory, "scaler.pkl")
        with open(model_path, "wb") as model_file:
            pickle.dump(self.model, model_file)
        with open(scaler_path, "wb") as scaler_file:
            pickle.dump(self.scaler, scaler_file)
        record = {
            "version": version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "model_type": self.model_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "candidate",
            "metrics": metrics,
            "n_train": dataset.get("n_train"),
            "n_test": dataset.get("n_test"),
            "model_path": model_path,
            "scaler_path": scaler_path,
        }
        register_candidate(record)
        return record
    
    @staticmethod
    def load(symbol: str, model_type: str = "rf", timeframe: str = "1h") -> 'ModelTrainer':
        """Load trained model from disk"""
        trainer = ModelTrainer(symbol, model_type, timeframe)
        
        active = get_active(symbol, timeframe, model_type)
        model_path = active["model_path"] if active else get_model_path(model_type, symbol, timeframe)
        scaler_path = active["scaler_path"] if active else get_scaler_path(symbol, timeframe)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        if not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Scaler not found: {scaler_path}")
        
        with open(model_path, 'rb') as f:
            trainer.model = pickle.load(f)
        
        with open(scaler_path, 'rb') as f:
            trainer.scaler = pickle.load(f)
        
        return trainer
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance if available"""
        if not hasattr(self.model, 'feature_importances_'):
            return {}
        
        importances = self.model.feature_importances_
        feature_names = [
            'sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi_14',
            'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'atr_14'
        ]
        
        return {
            name: float(imp)
            for name, imp in zip(feature_names, importances)
        }


async def train_model(
    dataset: Dict[str, Any],
    model_type: str = "rf",
    cv_folds: int = 5,
    promote: bool = False,
) -> Dict[str, Any]:
    """
    Train model on dataset
    
    Args:
        dataset: Dict from build_dataset() with train/test features and labels
        model_type: "logistic", "rf" (default), or "xgboost"
        cv_folds: Number of CV folds
    
    Returns:
        training results and metrics
    """
    
    def clean_value(val):
        """Clean NaN/inf values for JSON serialization"""
        if val is None or not np.isfinite(val) if isinstance(val, (int, float)) else False:
            return None
        return val
    
    symbol = dataset['symbol']
    
    # Prepare data
    X_train = np.array(dataset['train_features'], dtype=np.float32)
    y_train = np.array(dataset['train_labels'], dtype=np.int32)
    X_test = np.array(dataset['test_features'], dtype=np.float32)
    y_test = np.array(dataset['test_labels'], dtype=np.int32)

    if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
        raise ValueError("Dataset split must contain both classes for reliable training")
    
    # Train model
    trainer = ModelTrainer(symbol, model_type, dataset.get("timeframe", "1h"))
    train_metrics = trainer.fit(X_train, y_train, X_test, y_test)
    
    # Clean metrics
    train_metrics = {k: clean_value(v) if not isinstance(v, list) else v for k, v in train_metrics.items()}
    
    # Cross validation
    cv_metrics = trainer.cross_validate(X_train, y_train, cv=cv_folds)
    cv_metrics = {k: clean_value(v) for k, v in cv_metrics.items()}
    train_metrics.update(cv_metrics)
    
    # Feature importance
    feature_importance = trainer.get_feature_importance()
    feature_importance = {k: clean_value(v) for k, v in feature_importance.items()}
    
    # Save an immutable candidate. Promotion is explicit or performed by the retraining policy.
    candidate = trainer.save_version(train_metrics, dataset)
    if promote:
        candidate = approve_version(symbol, dataset.get("timeframe", "1h"), model_type, candidate["version"])
    
    return {
        "symbol": symbol,
        "timeframe": dataset.get("timeframe", "1h"),
        "model_type": model_type,
        "status": "trained",
        "n_train": dataset['n_train'],
        "n_test": dataset['n_test'],
        "n_features": dataset['n_features'],
        "feature_names": dataset['feature_names'],
        "metrics": train_metrics,
        "feature_importance": feature_importance,
        "model_path": candidate['model_path'],
        "scaler_path": candidate['scaler_path'],
        "version": candidate["version"],
        "approved": bool(promote),
    }
