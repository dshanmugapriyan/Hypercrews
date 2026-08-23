import os
import json
import datetime
import hashlib

REGISTRY_PATH = "app/resources/model_registry.json"

def get_file_checksum(filepath):
    if not os.path.exists(filepath):
        return None
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

class ModelRegistry:
    @staticmethod
    def _load_registry():
        if not os.path.exists(REGISTRY_PATH):
            return {}
        try:
            with open(REGISTRY_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def _save_registry(data):
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
        try:
            with open(REGISTRY_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving model registry: {e}")

    @classmethod
    def register_model(cls, model_name, model_version, artifact_path, feature_schema_version="1.0.0", metrics=None, is_production=True):
        registry = cls._load_registry()
        
        checksum = get_file_checksum(artifact_path)
        
        record = {
            "model_name": model_name,
            "model_version": model_version,
            "artifact_path": artifact_path,
            "feature_schema_version": feature_schema_version,
            "training_timestamp": datetime.datetime.now().isoformat(),
            "metrics": metrics or {},
            "is_production": is_production,
            "checksum": checksum
        }
        
        registry[model_name] = record
        cls._save_registry(registry)
        print(f"Model '{model_name}' version {model_version} registered successfully.")
        return record

    @classmethod
    def get_model_record(cls, model_name):
        registry = cls._load_registry()
        return registry.get(model_name)

    @classmethod
    def list_models(cls):
        registry = cls._load_registry()
        return list(registry.values())

    @classmethod
    def get_registered_models(cls):
        """Return registry dict keyed by model_name."""
        return cls._load_registry()
