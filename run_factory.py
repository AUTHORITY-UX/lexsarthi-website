# run_factory.py - Start the 250 Agent Factory
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import asyncio
import logging
from agent_factory import AgentFactory, FactoryScheduler, WebsiteIntegrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unknown_verdict.factory.main")

async def main():
    """Start the entire 250-agent factory."""
    logger.info("=" * 60)
    logger.info("🏭 UNKNOWN VERDICT v40.0 - 250 AGENT FACTORY")
    logger.info("⚖️ THE ADVOCACY – Global Law Firm")
    logger.info("🌐 www.advocacyalawfrim.in")
    logger.info("=" * 60)
    
    # Initialize factory
    factory = AgentFactory()
    await factory.initialize_agents()
    
    # Start scheduler
    scheduler = FactoryScheduler(factory)
    
    # Initialize website integrator
    website = WebsiteIntegrator()
    
    logger.info(f"✅ Factory ready with {len(factory.agents)} agents")
    logger.info("📋 Agent Breakdown:")
    for category, count in factory.get_factory_status()["agents_by_category"].items():
        logger.info(f"   ├─ {category.title()}: {count}")
    
    # Run the factory
    logger.info("\n🏭 Starting factory operations...")
    results = await factory.run_factory()
    
    # Report results
    successful = sum(1 for r in results if r.get("status") == "completed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    
    logger.info("\n📊 Factory Report:")
    logger.info(f"   ├─ Total Tasks: {len(results)}")
    logger.info(f"   ├─ Successful: {successful}")
    logger.info(f"   └─ Failed: {failed}")
    
    # Publish results to website
    for result in results:
        if result.get("status") == "completed":
            await website.publish_article({
                "title": result.get("task", "Legal Update"),
                "content": result.get("result", ""),
                "author": result.get("agent_name", "AI Agent"),
                "domain": result.get("domain", "Legal"),
                "timestamp": result.get("timestamp", datetime.now().isoformat())
            })
    
    logger.info("\n🔱 TRIDENT – PERMANENT ASSET – NEVER REMOVE")
    logger.info("⚖️ THE ADVOCACY – Global Law Firm")
    logger.info("🌐 www.advocacyalawfrim.in - Powered by Unknown Verdict v40.0")

if __name__ == "__main__":
    asyncio.run(main())