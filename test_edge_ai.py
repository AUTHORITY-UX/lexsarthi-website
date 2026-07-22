# test_edge_ai.py
"""
Comprehensive Edge AI Test Suite
Tests all Edge Impulse models and integrations
"""

import os
import sys
import json
import asyncio
import unittest
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edge_test")

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from edge_impulse_full import EdgeModelManager, EdgeResult, EdgeModelType

class TestEdgeAI(unittest.TestCase):
    """Test suite for Edge AI functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.manager = EdgeModelManager()
        cls.test_audio = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
        cls.test_image = np.random.randint(0, 255, 224*224*3, dtype=np.uint8).tobytes()
        
    def test_audio_classification(self):
        """Test audio classification"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.classify_audio(self.test_audio)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        self.assertGreater(result.classifications[0].confidence, 0)
        self.assertGreater(result.processing_time_ms, 0)
        
        logger.info(f"Audio classification: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_vision_classification(self):
        """Test vision classification"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.classify_vision(self.test_image)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        self.assertGreater(result.classifications[0].confidence, 0)
        
        logger.info(f"Vision classification: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_signature_verification(self):
        """Test signature verification"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.classify_signature(self.test_image)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertIn(result.classifications[0].label, ["verified", "suspicious", "error"])
        
        logger.info(f"Signature verification: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_emotion_detection(self):
        """Test emotion detection"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.analyze_emotion(self.test_audio)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        
        logger.info(f"Emotion detection: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_multi_modal(self):
        """Test multi-modal analysis"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.multi_modal_analysis(self.test_audio, self.test_image)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        
        logger.info(f"Multi-modal analysis: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_performance(self):
        """Test performance metrics"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run multiple predictions
        times = []
        for _ in range(10):
            start = datetime.now()
            loop.run_until_complete(
                self.manager.classify_audio(self.test_audio)
            )
            elapsed = (datetime.now() - start).total_seconds() * 1000
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        logger.info(f"Average inference time: {avg_time:.2f}ms")
        self.assertLess(avg_time, 100)  # Should be under 100ms

def run_edge_tests():
    """Run all Edge AI tests"""
    print("\n🧪 Running Edge AI Test Suite...")
    
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEdgeAI)
    result = runner.run(suite)
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success": result.wasSuccessful(),
        "details": {
            "failures": [f[0] for f in result.failures],
            "errors": [e[0] for e in result.errors]
        }
    }
    
    print("\n📊 Test Report:")
    print(json.dumps(report, indent=2))
    
    return report

if __name__ == "__main__":
    run_edge_tests()