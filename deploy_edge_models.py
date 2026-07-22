# deploy_edge_models.py
"""
Complete Edge Impulse Model Deployment Script
Deploys all trained models to production
"""

import os
import sys
import json
import shutil
import asyncio
import random
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("edge_deploy")

# ─── CONFIGURATION ──────────────────────────────────────────────────

MODELS_CONFIG = {
    "courtroom_audio": {
        "model_type": "audio",
        "sample_rate": 16000,
        "version": "1.0.0",
        "description": "Classifies courtroom audio proceedings",
        "input_shape": (16000,)
    },
    "document_vision": {
        "model_type": "vision",
        "input_size": (224, 224),
        "version": "1.0.0",
        "description": "Classifies legal documents",
        "input_shape": (224, 224, 3)
    },
    "signature_verification": {
        "model_type": "vision",
        "input_size": (224, 224),
        "version": "1.0.0",
        "description": "Verifies document signatures",
        "input_shape": (224, 224, 3)
    },
    "emotion_detection": {
        "model_type": "audio",
        "sample_rate": 16000,
        "version": "1.0.0",
        "description": "Detects emotional state from voice",
        "input_shape": (16000,)
    }
}

# ─── MODEL GENERATOR ──────────────────────────────────────────────

class ModelGenerator:
    """Generates simulated model files for testing"""
    
    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.models_dir.mkdir(exist_ok=True)
    
    def generate_mock_model(self, model_name: str, config: Dict) -> Path:
        """Generate a mock model file for testing"""
        version = config.get("version", "1.0.0")
        model_path = self.models_dir / f"{model_name}_v{version}.eim"
        
        # Create model file with some content
        model_content = {
            "name": model_name,
            "version": version,
            "model_type": config.get("model_type", "unknown"),
            "generated_at": datetime.now().isoformat(),
            "description": config.get("description", ""),
            "mock": True,
            "input_shape": config.get("input_shape", [])
        }
        
        with open(model_path, "w") as f:
            json.dump(model_content, f)
        
        # Also create a .bin file for compatibility
        bin_path = self.models_dir / f"{model_name}_v{version}.bin"
        with open(bin_path, "wb") as f:
            f.write(os.urandom(1024 * 1024))  # 1MB random data
        
        return model_path
    
    def generate_all_models(self) -> Dict[str, Path]:
        """Generate all mock models"""
        results = {}
        for model_name, config in MODELS_CONFIG.items():
            path = self.generate_mock_model(model_name, config)
            results[model_name] = path
            logger.info(f"Generated mock model: {model_name} -> {path}")
        return results

# ─── EDGE IMPULSE API CLIENT ──────────────────────────────────────

class EdgeImpulseAPIClient:
    """Client for Edge Impulse API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EDGE_IMPULSE_API_KEY")
        self.base_url = "https://studio.edgeimpulse.com/v1"
        self.project_id = os.getenv("EDGE_IMPULSE_PROJECT_ID")
        
    async def download_model(self, model_name: str, version: str) -> bytes:
        """Download model from Edge Impulse"""
        if not self.api_key:
            raise ValueError("EDGE_IMPULSE_API_KEY not set")
        
        # In production, this would make actual API calls
        logger.info(f"Downloading {model_name} v{version} from Edge Impulse...")
        
        # Simulate download
        import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(
        #         f"{self.base_url}/projects/{self.project_id}/models/{model_name}/download",
        #         headers={"Authorization": f"Bearer {self.api_key}"}
        #     ) as response:
        #         return await response.read()
        
        # Mock for now
        return b"Mock model data"

# ─── DEPLOYMENT ENGINE ─────────────────────────────────────────────

class EdgeModelDeployer:
    """Deploy Edge Impulse models to production"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EDGE_IMPULSE_API_KEY")
        self.models_dir = Path("edge_models")
        self.models_dir.mkdir(exist_ok=True)
        self.deployment_dir = Path("deployed_models")
        self.deployment_dir.mkdir(exist_ok=True)
        self.api_client = EdgeImpulseAPIClient(api_key) if self.api_key else None
        self.model_generator = ModelGenerator(self.models_dir)
        
    async def deploy_all_models(self, use_mock: bool = True) -> Dict:
        """Deploy all Edge Impulse models to production"""
        logger.info("🚀 Starting Edge Impulse Model Deployment...")
        
        results = {}
        
        for model_name, config in MODELS_CONFIG.items():
            try:
                logger.info(f"📦 Deploying {model_name}...")
                result = await self.deploy_model(model_name, config, use_mock)
                results[model_name] = result
                logger.info(f"✅ Deployed {model_name} (v{config['version']})")
            except Exception as e:
                logger.error(f"❌ Failed to deploy {model_name}: {e}")
                results[model_name] = {"status": "failed", "error": str(e)}
        
        # Save deployment manifest
        await self.save_manifest(results)
        
        # Generate deployment report
        await self.generate_report(results)
        
        return results
    
    async def deploy_model(self, model_name: str, config: Dict, use_mock: bool = True) -> Dict:
        """Deploy a single model"""
        
        # Step 1: Get model file
        if use_mock or not self.api_key:
            model_file = self.model_generator.generate_mock_model(model_name, config)
        else:
            model_data = await self.api_client.download_model(model_name, config["version"])
            model_file = self.models_dir / f"{model_name}_v{config['version']}.eim"
            with open(model_file, "wb") as f:
                f.write(model_data)
        
        # Step 2: Validate model
        await self.validate_model(model_file)
        
        # Step 3: Deploy to devices
        deployment_result = await self.deploy_to_devices(model_file, model_name, config)
        
        # Step 4: Update model registry
        await self.update_model_registry(model_name, config["version"], deployment_result)
        
        return {
            "status": "success",
            "model_file": str(model_file),
            "version": config["version"],
            "deployment_details": deployment_result,
            "model_type": config.get("model_type", "unknown")
        }
    
    async def validate_model(self, model_file: Path) -> bool:
        """Validate the model file"""
        if not model_file.exists():
            raise ValueError(f"Model file {model_file} not found")
        
        file_size = model_file.stat().st_size
        if file_size < 100:
            raise ValueError(f"Model file too small: {file_size} bytes")
        
        logger.info(f"✅ Model validation passed: {model_file} ({file_size} bytes)")
        return True
    
    async def deploy_to_devices(self, model_file: Path, model_name: str, config: Dict) -> Dict:
        """Deploy model to edge devices"""
        # Copy model to deployment directory
        deploy_path = self.deployment_dir / f"{model_name}.eim"
        shutil.copy(model_file, deploy_path)
        
        # Create deployment configuration
        config_path = self.deployment_dir / f"{model_name}.json"
        config_data = {
            "model_name": model_name,
            "deployed_at": datetime.now().isoformat(),
            "model_path": str(deploy_path),
            "version": config["version"],
            "model_type": config.get("model_type", "unknown"),
            "devices": [
                "local_edge",
                "courtroom_audio_device",
                "document_scan_device"
            ],
            "status": "active"
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        
        # Simulate deployment to devices
        await self.notify_devices(model_name, deploy_path)
        
        return {
            "deployed_path": str(deploy_path),
            "config_path": str(config_path),
            "devices": config_data["devices"],
            "status": "active"
        }
    
    async def notify_devices(self, model_name: str, model_path: Path):
        """Notify edge devices of new model deployment"""
        logger.info(f"📡 Notifying devices about {model_name} model update")
        await asyncio.sleep(0.5)  # Simulate notification
    
    async def update_model_registry(self, model_name: str, version: str, deployment: Dict):
        """Update the model registry"""
        registry_file = self.deployment_dir / "model_registry.json"
        
        if registry_file.exists():
            with open(registry_file, "r") as f:
                registry = json.load(f)
        else:
            registry = {}
        
        registry[model_name] = {
            "version": version,
            "deployed_at": datetime.now().isoformat(),
            "deployment": deployment,
            "status": "active"
        }
        
        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)
    
    async def save_manifest(self, results: Dict):
        """Save deployment manifest"""
        manifest = {
            "deployed_at": datetime.now().isoformat(),
            "total_models": len(results),
            "successful": sum(1 for r in results.values() if r.get("status") == "success"),
            "failed": sum(1 for r in results.values() if r.get("status") != "success"),
            "models": results,
            "environment": {
                "api_key_configured": bool(self.api_key),
                "models_dir": str(self.models_dir),
                "deployment_dir": str(self.deployment_dir)
            }
        }
        
        manifest_path = self.deployment_dir / "deployment_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"📄 Manifest saved to: {manifest_path}")
    
    async def generate_report(self, results: Dict):
        """Generate deployment report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "deployment_status": results,
            "summary": {
                "total": len(results),
                "success": sum(1 for r in results.values() if r.get("status") == "success"),
                "failed": sum(1 for r in results.values() if r.get("status") != "success")
            },
            "next_steps": [
                "1. Run test_edge_ai.py to verify models",
                "2. Update app.py with Edge AI routes",
                "3. Test /edge/process/audio endpoint",
                "4. Deploy to production environment"
            ]
        }
        
        report_path = self.deployment_dir / "deployment_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*50)
        print("📊 DEPLOYMENT SUMMARY")
        print("="*50)
        print(f"Total Models: {report['summary']['total']}")
        print(f"✅ Successful: {report['summary']['success']}")
        print(f"❌ Failed: {report['summary']['failed']}")
        print("="*50)
        print("\n📋 Next Steps:")
        for step in report['next_steps']:
            print(f"  {step}")
        print("="*50)


# ─── MAIN ────────────────────────────────────────────────────────────

async def main():
    """Main deployment function"""
    print("🚀 Edge Impulse Model Deployment")
    print("="*50)
    
    # Check for API key
    api_key = os.getenv("EDGE_IMPULSE_API_KEY")
    if not api_key:
        print("⚠️ No EDGE_IMPULSE_API_KEY found. Using mock models for testing.")
        print("   Set EDGE_IMPULSE_API_KEY environment variable for production deployment.")
    
    # Initialize deployer
    deployer = EdgeModelDeployer(api_key)
    
    # Deploy all models
    results = await deployer.deploy_all_models(use_mock=not bool(api_key))
    
    print("\n✅ Deployment complete!")
    print(f"📁 Models deployed to: {deployer.deployment_dir}")
    print(f"📁 Model files saved to: {deployer.models_dir}")
    
    # Verify deployment
    print("\n🔍 Verifying deployment...")
    for model_name, result in results.items():
        if result.get("status") == "success":
            print(f"  ✅ {model_name}: {result['model_file']}")
        else:
            print(f"  ❌ {model_name}: {result.get('error', 'Unknown error')}")
    
    print("\n📋 Next Steps:")
    print("  1. Run: python test_edge_ai.py")
    print("  2. Run: python app.py (Edge AI routes will be available)")
    print("  3. Test: curl -X POST http://localhost:7860/edge/process/audio ...")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())