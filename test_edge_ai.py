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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("edge_test")

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Edge AI modules
try:
    from edge_impulse_full import EdgeModelManager, EdgeResult, EdgeAIService
    EDGE_IMPORTED = True
except ImportError as e:
    EDGE_IMPORTED = False
    logger.error(f"Failed to import edge_impulse_full: {e}")

class TestEdgeAI(unittest.TestCase):
    """Test suite for Edge AI functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        if not EDGE_IMPORTED:
            raise unittest.SkipTest("edge_impulse_full module not available")
        
        cls.manager = EdgeModelManager()
        cls.service = EdgeAIService()
        
        # Test data
        cls.test_audio = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
        cls.test_image = np.random.randint(0, 255, 224*224*3, dtype=np.uint8).tobytes()
        cls.test_empty_audio = b''
        cls.test_empty_image = b''
        
        logger.info("✅ Test environment initialized")
    
    def test_audio_classification(self):
        """Test audio classification"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.classify_audio(self.test_audio)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        self.assertGreaterEqual(result.classifications[0].confidence, 0)
        self.assertGreater(result.processing_time_ms, 0)
        
        logger.info(f"✅ Audio classification: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_audio_with_empty_data(self):
        """Test audio classification with empty data"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.classify_audio(self.test_empty_audio)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        logger.info(f"✅ Empty audio classification: {result.classifications[0].label}")
    
    def test_vision_classification(self):
        """Test vision classification"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.classify_vision(self.test_image)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        self.assertGreaterEqual(result.classifications[0].confidence, 0)
        
        logger.info(f"✅ Vision classification: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_signature_verification(self):
        """Test signature verification"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.classify_signature(self.test_image)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        
        logger.info(f"✅ Signature verification: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_emotion_detection(self):
        """Test emotion detection"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.analyze_emotion(self.test_audio)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        
        logger.info(f"✅ Emotion detection: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_multi_modal(self):
        """Test multi-modal analysis"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.manager.multi_modal_analysis(self.test_audio, self.test_image)
        )
        
        self.assertIsInstance(result, EdgeResult)
        self.assertGreater(len(result.classifications), 0)
        
        logger.info(f"✅ Multi-modal analysis: {result.classifications[0].label} ({result.classifications[0].confidence:.2f})")
    
    def test_service_methods(self):
        """Test EdgeAIService methods"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test document processing
        doc_result = loop.run_until_complete(
            self.service.process_legal_document(self.test_image)
        )
        self.assertIsInstance(doc_result, dict)
        self.assertIn("classification", doc_result)
        logger.info(f"✅ Document processing: {doc_result['classification']}")
        
        # Test signature verification
        sig_result = loop.run_until_complete(
            self.service.verify_signature(self.test_image)
        )
        self.assertIsInstance(sig_result, dict)
        self.assertIn("verified", sig_result)
        logger.info(f"✅ Signature verification: {sig_result['verified']}")
        
        # Test courtroom audio
        audio_result = loop.run_until_complete(
            self.service.analyze_courtroom_audio(self.test_audio)
        )
        self.assertIsInstance(audio_result, dict)
        self.assertIn("proceeding_type", audio_result)
        logger.info(f"✅ Courtroom audio: {audio_result['proceeding_type']}")
        
        # Test emotion detection
        emotion_result = loop.run_until_complete(
            self.service.detect_emotion(self.test_audio)
        )
        self.assertIsInstance(emotion_result, dict)
        self.assertIn("emotion", emotion_result)
        logger.info(f"✅ Emotion detection: {emotion_result['emotion']}")
    
    def test_performance(self):
        """Test performance metrics"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run multiple predictions
        times = []
        for _ in range(5):
            start = datetime.now()
            loop.run_until_complete(
                self.manager.classify_audio(self.test_audio)
            )
            elapsed = (datetime.now() - start).total_seconds() * 1000
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        logger.info(f"⏱️ Average inference time: {avg_time:.2f}ms")
        self.assertLess(avg_time, 500)  # Should be under 500ms in simulation
    
    def test_metrics(self):
        """Test metrics collection"""
        metrics = self.service.get_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn("total_predictions", metrics)
        self.assertIn("simulation_mode", metrics)
        logger.info(f"📊 Metrics: {metrics['total_predictions']} predictions, {metrics.get('avg_latency_ms', 0):.2f}ms avg")

def run_edge_tests():
    """Run all Edge AI tests"""
    print("\n" + "="*60)
    print("🧪 Running Edge AI Test Suite")
    print("="*60)
    
    # Check imports
    if not EDGE_IMPORTED:
        print("❌ edge_impulse_full module not available. Tests skipped.")
        return {"status": "skipped", "reason": "Module not available"}
    
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
    
    print("\n" + "="*60)
    print("📊 Test Report")
    print("="*60)
    print(f"Tests Run: {report['tests_run']}")
    print(f"✅ Success: {report['success']}")
    print(f"❌ Failures: {report['failures']}")
    print(f"⚠️ Errors: {report['errors']}")
    print("="*60)
    
    return report

if __name__ == "__main__":
    # Run tests
    report = run_edge_tests()
    
    # Save report
    report_path = Path("test_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Test report saved to: {report_path}")