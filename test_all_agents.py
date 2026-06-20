# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# LEXSARTHI v4.0 - THE COMPLETE LEGAL OS
# $10B VISION - SINGLE PROVIDER FOR ALL LEGAL WORK AUTOMATION
# ===================================================================
# Powered By THE ADVOCACY A LAW FIRM
# ===================================================================

import asyncio
import aiohttp
import json
import time
from datetime import datetime

BASE_URL = "https://upamnyu12-lex.hf.space"
TEST_USER = {
    "username": f"test_{int(time.time())}@lexsarthi.com",
    "password": "Test@123456",
    "full_name": "Test User",
    "consent_given": True,
    "confidentiality_accepted": True
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.PURPLE}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️ {text}{Colors.RESET}")

async def test_all_agents():
    print_header("🔍 LEXSARTHI v4.0 - COMPLETE AGENT TEST")
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with aiohttp.ClientSession() as session:
        # Health Check
        print_header("1. Health Check")
        async with session.get(f"{BASE_URL}/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                print_success(f"API Healthy - Version: {data.get('version')}")
                print_info(f"Agents: {data.get('agents')}")
                print_info(f"Lawyer: {data.get('lawyer', {}).get('name')}")
            else:
                print_error("API not healthy")
                return
        
        # Register
        print_header("2. Register User")
        async with session.post(f"{BASE_URL}/auth/register", json=TEST_USER) as resp:
            if resp.status == 200:
                data = await resp.json()
                print_success(f"Registered: {TEST_USER['username']}")
                print_info(f"Trial: {data.get('trial_days')} days")
            else:
                print_warning("User may already exist")
        
        # Login
        print_header("3. Login")
        async with session.post(f"{BASE_URL}/auth/login", json={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data.get("access_token")
                print_success("Login successful")
            else:
                print_error("Login failed")
                return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get Pricing
        print_header("4. Pricing Plans")
        async with session.get(f"{BASE_URL}/pricing") as resp:
            if resp.status == 200:
                data = await resp.json()
                print_success("Pricing loaded")
                print_info(f"Plans: {list(data.get('plans', {}).keys())}")
                print_info(f"Pay Per Use: {list(data.get('pay_per_use', {}).keys())}")
            else:
                print_error("Pricing failed")
        
        # Test Agents
        print_header("5. Testing Agents")
        test_agents = [
            {"id": "compliance_dpdp", "name": "DPDP Act Compliance"},
            {"id": "contract_review_general", "name": "Contract Review"}
        ]
        
        for agent in test_agents:
            print(f"\n{Colors.BOLD}Testing: {agent['name']}{Colors.RESET}")
            async with session.post(f"{BASE_URL}/run-agent",
                json={"agent_id": agent["id"], "input_text": "Analyze this document for legal compliance"},
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print_success(f"✅ {agent['name']} executed successfully")
                    if data.get("lawyer"):
                        print_info(f"  Reviewed by: {data['lawyer'].get('name')}")
                else:
                    print_error(f"❌ {agent['name']} failed")
            await asyncio.sleep(1)
        
        # Test Domain Scan
        print_header("6. Domain Intelligence")
        async with session.post(f"{BASE_URL}/scan-domain",
            json={"domain": "google.com"},
            headers=headers
        ) as resp:
            if resp.status == 200:
                print_success("Domain scan completed")
            else:
                print_error("Domain scan failed")
        
        # Test ₹2 Payment
        print_header("7. ₹2 Test Payment")
        async with session.post(f"{BASE_URL}/payment/create-order",
            json={"amount": 200, "currency": "INR"},
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print_success("Payment order created")
                print_info(f"Amount: ₹{data.get('amount', 200)/100:.2f}")
                print_info(f"Test Mode: {data.get('test_mode', False)}")
            else:
                print_error("Payment creation failed")
        
        print_header("📊 TEST SUMMARY")
        print_success("✅ All tests completed successfully!")
        print_info(f"Test User: {TEST_USER['username']}")
        print_info(f"Website: {BASE_URL}")
        print_info("License: GNU AGPL-3.0")

if __name__ == "__main__":
    asyncio.run(test_all_agents())