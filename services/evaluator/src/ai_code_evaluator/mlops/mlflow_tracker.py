from __future__ import annotations

import logging
import os
from typing import Any, Protocol

import mlflow

logger = logging.getLogger(__name__)

class ExperimentTracker(Protocol):
    def create_experiment(self, name: str) -> str: ...
    def start_run(self, experiment_id: str, run_name: str | None = None) -> Any: ...
    def log_param(self, key: str, value: Any) -> None: ...
    def log_params(self, params: dict[str, Any]) -> None: ...
    def log_metric(self, key: str, value: float) -> None: ...
    def log_metrics(self, metrics: dict[str, float]) -> None: ...
    def end_run(self, status: str = "FINISHED") -> None: ...


class MLflowTracker:
    def __init__(self, tracking_uri: str | None = None):
        uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(uri)
        self.active_run = None

    def create_experiment(self, name: str) -> str:
        try:
            exp = mlflow.get_experiment_by_name(name)
            if exp:
                return exp.experiment_id
            return mlflow.create_experiment(name)
        except Exception as e:
            logger.warning(f"Failed to create MLflow experiment '{name}': {e}")
            return ""

    def start_run(self, experiment_id: str, run_name: str | None = None) -> Any:
        try:
            if not experiment_id:
                return None
            self.active_run = mlflow.start_run(experiment_id=experiment_id, run_name=run_name)
            return self.active_run
        except Exception as e:
            logger.warning(f"Failed to start MLflow run: {e}")
            return None

    def log_param(self, key: str, value: Any) -> None:
        try:
            if self.active_run:
                mlflow.log_param(key, value)
        except Exception as e:
            logger.warning(f"Failed to log MLflow param '{key}': {e}")

    def log_params(self, params: dict[str, Any]) -> None:
        try:
            if self.active_run:
                mlflow.log_params(params)
        except Exception as e:
            logger.warning(f"Failed to log MLflow params: {e}")

    def log_metric(self, key: str, value: float) -> None:
        try:
            if self.active_run:
                mlflow.log_metric(key, value)
        except Exception as e:
            logger.warning(f"Failed to log MLflow metric '{key}': {e}")

    def log_metrics(self, metrics: dict[str, float]) -> None:
        try:
            if self.active_run:
                mlflow.log_metrics(metrics)
        except Exception as e:
            logger.warning(f"Failed to log MLflow metrics: {e}")

    def end_run(self, status: str = "FINISHED") -> None:
        try:
            if self.active_run:
                mlflow.end_run(status=status)
                self.active_run = None
        except Exception as e:
            logger.warning(f"Failed to end MLflow run: {e}")
