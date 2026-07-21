# =============================================================================
# akida_edge.py – BrainChip Akida Integration
# =============================================================================

import os
import json
import logging
import numpy as np
from typing import List, Dict, Optional
from typing import Optional, Dict, List, Any

logger = logging.getLogger("unknown_verdict.akida")

try:
    import akida
    from akida import Model, Device
    AKIDA_AVAILABLE = True
except ImportError:
    AKIDA_AVAILABLE = False
    logger.warning("Akida SDK not installed. Running in simulation mode.")

class AkidaEdge:
    """
    BrainChip Akida Edge AI Box integration.
    Provides ultra-low-power (<1W) inference for legal AI.
    """
    
    def __init__(self):
        self.akida_available = AKIDA_AVAILABLE
        self.model = None
        self.device = None
        self.is_initialized = False
        
        if self.akida_available:
            self._initialize_akida()
    
    def _initialize_akida(self):
        """Initialize Akida device and load model"""
        try:
            # Detect available devices
            devices = akida.list_devices()
            if devices:
                self.device = akida.open_device(devices[0])
                logger.info(f"✅ Akida device found: {devices[0]}")
                
                # Load model if exists
                model_path = os.getenv("AKIDA_MODEL_PATH", "models/legal_classifier.fbz")
                if os.path.exists(model_path):
                    self.model = Model(model_path)
                    self.device.map_model(self.model)
                    self.is_initialized = True
                    logger.info("✅ Akida model loaded successfully")
                else:
                    logger.warning(f"⚠️ Akida model not found at {model_path}")
            else:
                logger.warning("⚠️ No Akida devices found. Running in simulation mode.")
        except Exception as e:
            logger.error(f"❌ Akida initialization failed: {e}")
    
    async def classify_intent(self, text: str) -> Dict:
        """
        Classify legal intent using Akida NPU.
        Returns: {"domain": str, "confidence": float, "energy_used": float}
        """
        if not self.is_initialized:
            return self._simulate_classification(text)
        
        try:
            # Convert text to features
            features = self._text_to_features(text)
            
            # Run inference on Akida
            outputs = self.device.predict(features)
            
            # Get classification results
            domains = ["constitutional", "contract", "criminal", "corporate", "tax", "general"]
            predictions = outputs[0]
            domain_idx = np.argmax(predictions)
            
            return {
                "domain": domains[domain_idx],
                "confidence": float(predictions[domain_idx]),
                "energy_used": 0.0001  # ~0.1mW per inference
            }
        except Exception as e:
            logger.error(f"Akida inference failed: {e}")
            return self._simulate_classification(text)
    
    def _text_to_features(self, text: str) -> np.ndarray:
        """Convert text to feature vector for Akida"""
        # Simplified: use bag-of-words with legal keywords
        # In production, use the Edge Impulse trained model
        keywords = {
            "constitutional": ["constitution", "fundamental", "rights", "article", "amendment"],
            "contract": ["contract", "agreement", "breach", "remedy", "specific relief"],
            "criminal": ["ipc", "crpc", "criminal", "offence", "punishment", "bail"],
            "corporate": ["company", "board", "shareholder", "m&a", "insolvency"],
            "tax": ["gst", "income tax", "customs", "excise", "taxation"]
        }
        
        features = []
        text_lower = text.lower()
        for domain, kws in keywords.items():
            score = sum(1 for kw in kws if kw in text_lower)
            features.append(score)
        
        # Pad to 384 (expected by Akida model)
        features = np.array(features + [0] * (384 - len(features)), dtype=np.float32)
        return features.reshape(1, -1)
    
    def _simulate_classification(self, text: str) -> Dict:
        """Simulate classification when Akida is not available"""
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
        confidence = min(0.95, 0.5 + scores.get(best, 0) * 0.1)
        
        return {
            "domain": best,
            "confidence": confidence,
            "energy_used": 0.001  # Simulated energy
        }
    
    async def is_available(self) -> bool:
        """Check if Akida is available and initialized"""
        return self.is_initialized