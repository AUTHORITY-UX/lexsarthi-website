# =============================================================================
# edge_impulse_model.py – Edge Impulse Trained Model Loader
# =============================================================================

import os
import json
import logging
import numpy as np
from typing import Dict, Optional

logger = logging.getLogger("unknown_verdict.edgeimpulse")

class EdgeImpulseModel:
    """
    Load and run Edge Impulse trained model for legal document classification.
    """
    
    def __init__(self):
        self.model = None
        self.model_type = None
        self.features = None
        self.classes = []
        self.is_loaded = False
        
        self._load_model()
    
    def _load_model(self):
        """Load Edge Impulse trained model"""
        # Check for model formats
        model_paths = [
            "models/edge_impulse_model.tflite",
            "models/legal_classifier.tflite",
            "models/legal_intent_model.tflite"
        ]
        
        for path in model_paths:
            if os.path.exists(path):
                try:
                    import tflite_runtime.interpreter as tflite
                    self.model = tflite.Interpreter(model_path=path)
                    self.model.allocate_tensors()
                    
                    # Get input/output details
                    self.input_details = self.model.get_input_details()
                    self.output_details = self.model.get_output_details()
                    
                    # Load classes
                    class_file = path.replace(".tflite", "_classes.json")
                    if os.path.exists(class_file):
                        with open(class_file) as f:
                            self.classes = json.load(f)
                    else:
                        self.classes = ["constitutional", "contract", "criminal", "corporate", "tax", "general", "family", "property", "cyber", "arbitration"]
                    
                    self.is_loaded = True
                    logger.info(f"✅ Edge Impulse model loaded from {path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load {path}: {e}")
        
        logger.warning("⚠️ No Edge Impulse model found. Using fallback.")
    
    async def predict(self, text: str) -> Dict:
        """
        Run inference on Edge Impulse model.
        Returns: {"class": str, "confidence": float, "all_scores": List[float]}
        """
        if not self.is_loaded:
            return self._fallback_prediction(text)
        
        try:
            # Preprocess text
            input_data = self._preprocess_text(text)
            
            # Run inference
            self.model.set_tensor(self.input_details[0]['index'], input_data)
            self.model.invoke()
            
            # Get output
            output_data = self.model.get_tensor(self.output_details[0]['index'])
            
            # Get predictions
            predictions = output_data[0]
            class_idx = np.argmax(predictions)
            confidence = float(predictions[class_idx])
            
            return {
                "class": self.classes[class_idx] if class_idx < len(self.classes) else "general",
                "confidence": confidence,
                "all_scores": predictions.tolist()
            }
        except Exception as e:
            logger.error(f"Edge Impulse inference failed: {e}")
            return self._fallback_prediction(text)
    
    def _preprocess_text(self, text: str) -> np.ndarray:
        """Preprocess text for Edge Impulse model"""
        # Simplified: use TF-IDF style features
        # In production, use the same preprocessing as training
        keywords = {
            "constitutional": ["constitution", "rights", "article", "amendment", "federal", "judicial"],
            "contract": ["contract", "agreement", "breach", "remedy", "specific relief", "offer", "acceptance"],
            "criminal": ["ipc", "crpc", "criminal", "offence", "punishment", "bail", "evidence"],
            "corporate": ["company", "board", "shareholder", "m&a", "insolvency", "sebi", "director"],
            "tax": ["gst", "income tax", "customs", "excise", "taxation", "deduction"],
            "family": ["marriage", "divorce", "custody", "maintenance", "adoption"],
            "property": ["property", "land", "lease", "rent", "mortgage", "transfer"],
            "cyber": ["cyber", "data", "privacy", "digital", "internet", "hacking"],
            "arbitration": ["arbitration", "mediation", "conciliation", "dispute", "award"]
        }
        
        text_lower = text.lower()
        features = []
        for kws in keywords.values():
            score = sum(1 for kw in kws if kw in text_lower)
            features.append(score)
        
        # Normalize and pad
        features = np.array(features, dtype=np.float32)
        features = features / (len(text.split()) + 1)
        features = np.pad(features, (0, 384 - len(features)), constant_values=0)
        
        return features.reshape(1, -1)
    
    def _fallback_prediction(self, text: str) -> Dict:
        """Fallback when model is not loaded"""
        domains = ["constitutional", "contract", "criminal", "corporate", "tax", "general"]
        keywords = {
            "constitutional": ["constitution", "rights", "article", "amendment"],
            "contract": ["contract", "agreement", "breach", "remedy"],
            "criminal": ["ipc", "crpc", "criminal", "offence"],
            "corporate": ["company", "board", "shareholder", "m&a"],
            "tax": ["gst", "tax", "customs", "excise"]
        }
        
        text_lower = text.lower()
        scores = {}
        for domain, kws in keywords.items():
            scores[domain] = sum(1 for kw in kws if kw in text_lower)
        
        best = max(scores, key=scores.get) if scores else "general"
        total = sum(scores.values()) or 1
        
        return {
            "class": best,
            "confidence": scores.get(best, 0) / total,
            "all_scores": [scores.get(d, 0) / total for d in domains]
        }