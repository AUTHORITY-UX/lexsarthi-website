#!/usr/bin/env python3
# ===================================================================
# 🔱 LEXSARTHI v4.0 - TEST SUITE
# ===================================================================
# Copyright (c) 2026 THE ADVOCACY - A LAW FIRM. All rights reserved.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY - A LAW FIRM.
# ===================================================================
# 🏛️ OWNED BY: THE ADVOCACY - A LAW FIRM
# 📜 UDYAM: UDYAM-UP-09-0043193 | PAN: CHFPK3464A
# 👤 PROPRIETOR: UPMANYU KUMAR | ESTABLISHED: 2026
# ===================================================================
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================

import requests
import json
import sys

BASE_URL = "https://upamnyu12-lex.hf.space"
# BASE_URL = "http://localhost:7860"  # For local testing

def test_health():
    print("📌 Testing: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ PASSED - {data.get('status')}")
        print(f"   🤖 Agents: {data.get('agents')}")
        print(f"   ✅ Verifiers: {data.get('verifiers')}")
        print(f"   🎯 Accuracy: {data.get('accuracy')}")
        print(f"   💳 Razorpay: {data.get('razorpay')}")
        return True
    else:
        print(f"   ❌ FAILED")
        return False

def test_agents():
    print("\n📌 Testing: Agents List")
    response = requests.get(f"{BASE_URL}/agents")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ PASSED - Total: {data.get('total')} agents")
        print(f"   🏛️ Firm: {data.get('firm')}")
        return True
    else:
        print(f"   ❌ FAILED")
        return False

def test_verifiers():
    print("\n📌 Testing: Verifiers List")
    response = requests.get(f"{BASE_URL}/verifiers")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ PASSED - Total: {data.get('total')} verifiers")
        return True
    else:
        print(f"   ❌ FAILED")
        return False

def test_root():
    print("\n📌 Testing: Root Endpoint")
    response = requests.get(f"{BASE_URL}/")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ PASSED - {data.get('name')}")
        print(f"   🏛️ Firm: {data.get('firm')}")
        print(f"   📜 UDYAM: {data.get('udyam')}")
        print(f"   🔱 TRIDENT: {data.get('trident')}")
        return True
    else:
        print(f"   ❌ FAILED")
        return False

def test_ask():
    print("\n📌 Testing: Query")
    response = requests.post(
        f"{BASE_URL}/ask",
        data={"query": "What is the Indian Contract Act?"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ PASSED")
        print(f"   📊 Response Length: {len(data.get('response', ''))} chars")
        print(f"   🤖 Agents Used: {data.get('agents_used')}")
        print(f"   ✅ Verifiers: {data.get('verifiers_passed')}")
        print(f"   🎯 Accuracy: {data.get('accuracy')}")
        return True
    else:
        print(f"   ❌ FAILED")
        return False

def main():
    print("=" * 70)
    print("🔱 LEXSARTHI v4.0 - TEST SUITE")
    print("🏛️ THE ADVOCACY - A LAW FIRM")
    print("=" * 70)
    
    tests = [
        test_root,
        test_health,
        test_agents,
        test_verifiers,
        test_ask
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"✅ PASSED: {passed}/{len(tests)}")
    print(f"❌ FAILED: {len(tests) - passed}/{len(tests)}")
    print("=" * 70)
    
    if passed == len(tests):
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("⚠️ SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()

# ===================================================================
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ===================================================================