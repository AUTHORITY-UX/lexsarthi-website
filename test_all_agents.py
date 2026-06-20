# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# LEXSARTHI v4.0 - COMPLETE AGENT TEST SCRIPT
# ===================================================================

import requests
import json
import time
import sys
from datetime import datetime

# ===================================================================
# Configuration
# ===================================================================
API_BASE = "https://upamnyu12-lex.hf.space"
TEST_EMAIL = "test.agent@test.com"
TEST_PASSWORD = "Test@123456"
TEST_USERNAME = "testagent"

# ===================================================================
# All Agents to Test
# ===================================================================
ALL_AGENTS = [
    {"id": "contract_review", "name": "Contract Review Expert", "category": "Legal Intelligence"},
    {"id": "case_analysis", "name": "Case Law Analysis Expert", "category": "Legal Intelligence"},
    {"id": "legal_research", "name": "Legal Research Expert", "category": "Legal Intelligence"},
    {"id": "compliance_check", "name": "Compliance Check Expert", "category": "Legal Intelligence"},
    {"id": "judgment_drafting", "name": "Judgment Drafting Expert", "category": "Legal Intelligence"},
    {"id": "legal_document_analysis", "name": "Legal Document Analysis Expert", "category": "Legal Intelligence"},
    {"id": "risk_assessment", "name": "Risk Assessment Expert", "category": "Legal Intelligence"},
    {"id": "regulatory_advice", "name": "Regulatory Compliance Expert", "category": "Legal Intelligence"},
    {"id": "merger_acquisition", "name": "M&A Legal Expert", "category": "Corporate Law"},
    {"id": "intellectual_property", "name": "IP Law Expert", "category": "Corporate Law"},
    {"id": "tax_law", "name": "Tax Law Expert", "category": "Corporate Law"},
    {"id": "corporate_law", "name": "Corporate Law Expert", "category": "Corporate Law"},
    {"id": "employment_law", "name": "Employment Law Expert", "category": "Corporate Law"},
    {"id": "real_estate_law", "name": "Real Estate Law Expert", "category": "Corporate Law"},
    {"id": "family_law", "name": "Family Law Expert", "category": "Personal Law"},
    {"id": "criminal_law", "name": "Criminal Law Expert", "category": "Personal Law"},
    {"id": "constitutional_law", "name": "Constitutional Law Expert", "category": "Public Law"},
    {"id": "international_law", "name": "International Law Expert", "category": "Public Law"},
    {"id": "arbitration", "name": "Arbitration Expert", "category": "Dispute Resolution"},
    {"id": "mediation", "name": "Mediation Expert", "category": "Dispute Resolution"},
    {"id": "domain_intelligence", "name": "Domain Intelligence Expert", "category": "Technology"},
    {"id": "market_intelligence", "name": "Market Intelligence Expert", "category": "Technology"},
    {"id": "trade_analysis", "name": "Trade Analysis Expert", "category": "Technology"},
    {"id": "campaign_tools", "name": "Campaign Tools Expert", "category": "Technology"},
    {"id": "self_analytics", "name": "Self-Data Analytics Expert", "category": "Technology"},
    {"id": "daily_reports", "name": "Daily Reports Expert", "category": "Technology"},
]

# ===================================================================
# Test Results
# ===================================================================
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.results = []
    
    def add_result(self, test_name, status, message, data=None):
        self.total += 1
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
        self.results.append({
            "test": test_name,
            "status": status,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

results = TestResults()

# ===================================================================
# Utility Functions
# ===================================================================
def print_header(text):
    print("\n" + "=" * 80)
    print("🔹 " + text)
    print("=" * 80)

def print_success(text):
    print("✅ " + text)

def print_error(text):
    print("❌ " + text)

def print_warning(text):
    print("⚠️ " + text)

def print_info(text):
    print("ℹ️ " + text)

# ===================================================================
# API Client
# ===================================================================
class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
    
    def register(self, email, username, password):
        print_info("Registering user: " + email)
        url = self.base_url + "/auth/register"
        payload = {
            "email": email,
            "username": username,
            "password": password,
            "full_name": "Test Agent User",
            "user_type": "individual",
            "consent_dpdp": True,
            "consent_marketing": False,
            "consent_analytics": True,
            "consent_third_party": False,
            "acknowledge_privacy_policy": True,
            "acknowledge_terms": True,
            "acknowledge_zero_retention": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.user_id = data.get("user", {}).get("id")
                print_success("User registered successfully! User ID: " + str(self.user_id))
                return True
            else:
                print_error("Registration failed: " + str(response.status_code) + " - " + response.text)
                return False
        except Exception as e:
            print_error("Registration error: " + str(e))
            return False
    
    def login(self, email, password):
        print_info("Logging in: " + email)
        url = self.base_url + "/auth/login"
        payload = {"email": email, "password": password}
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.user_id = data.get("user", {}).get("id")
                print_success("Login successful! User ID: " + str(self.user_id))
                return True
            else:
                print_error("Login failed: " + str(response.status_code) + " - " + response.text)
                return False
        except Exception as e:
            print_error("Login error: " + str(e))
            return False
    
    def get_headers(self):
        if not self.access_token:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.access_token
        }
    
    def test_endpoint(self, method, endpoint, data=None):
        url = self.base_url + endpoint
        try:
            start_time = time.time()
            
            if method.upper() == "GET":
                response = requests.get(url, headers=self.get_headers(), timeout=15)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=self.get_headers(), timeout=15)
            else:
                return False, "Unknown method", None
            
            elapsed = time.time() - start_time
            
            if response.status_code in [200, 201, 204]:
                try:
                    response_data = response.json()
                except:
                    response_data = {"status": "success", "raw": response.text}
                return True, "OK (" + str(response.status_code) + ") - " + "{:.2f}".format(elapsed) + "s", response_data
            else:
                return False, "Error " + str(response.status_code) + " - " + response.text[:100], None
        except Exception as e:
            return False, "Exception: " + str(e), None

# ===================================================================
# Test Functions
# ===================================================================
def test_health(client):
    print_header("Testing Health Endpoint")
    success, message, data = client.test_endpoint("GET", "/health")
    if success and data:
        print_success("Health Check: " + data.get('status', 'unknown'))
        print_info("Version: " + data.get('version', 'unknown'))
        print_info("Agents: " + str(data.get('agents', 'unknown')))
        results.add_result("Health Check", "PASS", message, data)
    else:
        print_error("Health Check Failed: " + message)
        results.add_result("Health Check", "FAIL", message)

def test_root(client):
    print_header("Testing Root Endpoint")
    success, message, data = client.test_endpoint("GET", "/")
    if success and data:
        print_success("Root: " + data.get('service', 'unknown'))
        print_info("Version: " + data.get('version', 'unknown'))
        print_info("Agents: " + str(data.get('agents', 'unknown')))
        results.add_result("Root Endpoint", "PASS", message, data)
    else:
        print_error("Root Failed: " + message)
        results.add_result("Root Endpoint", "FAIL", message)

def test_list_agents(client):
    print_header("Testing List Agents Endpoint")
    success, message, data = client.test_endpoint("GET", "/agents")
    if success and data:
        agents = data.get('agents', [])
        total = data.get('total', 0)
        categories = data.get('categories', [])
        print_success("Found " + str(total) + " agents across " + str(len(categories)) + " categories")
        for category in categories:
            count = len([a for a in agents if a.get('category') == category])
            print_info("  " + category + ": " + str(count) + " agents")
        results.add_result("List Agents", "PASS", message, data)
    else:
        print_error("List Agents Failed: " + message)
        results.add_result("List Agents", "FAIL", message)

def test_agent_run(client, agent_id, agent_name):
    print_info("Testing Agent: " + agent_name + " (" + agent_id + ")")
    
    test_data = {
        "agent_type": agent_id,
        "input_data": {
            "query": "Test query for " + agent_name,
            "context": "This is a test run to verify the agent is working"
        },
        "context": {"test": True, "timestamp": datetime.now().isoformat()}
    }
    
    success, message, data = client.test_endpoint("POST", "/agent/run", test_data)
    
    if success and data:
        print_success("✅ " + agent_name + ": SUCCESS")
        results.add_result("Agent: " + agent_name, "PASS", message, data)
        return True
    else:
        print_error("❌ " + agent_name + ": FAILED - " + message)
        results.add_result("Agent: " + agent_name, "FAIL", message)
        return False

def test_all_agents(client):
    print_header("Testing All " + str(len(ALL_AGENTS)) + " Agents")
    
    passed = 0
    failed = 0
    
    for agent in ALL_AGENTS:
        if test_agent_run(client, agent['id'], agent['name']):
            passed += 1
        else:
            failed += 1
        time.sleep(0.5)
    
    print_info("Agent Test Summary: " + str(passed) + " passed, " + str(failed) + " failed")

def test_domain_scan(client):
    print_header("Testing Domain Scan")
    
    test_domains = ["google.com", "github.com"]
    
    for domain in test_domains:
        print_info("Scanning domain: " + domain)
        data = {"domain": domain}
        success, message, data = client.test_endpoint("POST", "/scan-domain", data)
        if success and data:
            print_success("Domain " + domain + ": Scan successful")
            results.add_result("Domain Scan: " + domain, "PASS", message, data)
        else:
            print_error("Domain " + domain + " scan failed: " + message)
            results.add_result("Domain Scan: " + domain, "FAIL", message)
        time.sleep(0.5)

def test_legal_query(client):
    print_header("Testing Legal Query")
    
    test_queries = [
        "What are the key provisions of DPDP Act 2023?",
        "Explain the concept of attorney-client privilege",
    ]
    
    for query in test_queries:
        print_info("Legal Query: " + query[:50] + "...")
        data = {
            "query": query,
            "agent_type": "legal_research",
            "context": {"test": True}
        }
        success, message, data = client.test_endpoint("POST", "/legal/query", data)
        if success and data:
            print_success("✅ Query successful")
            results.add_result("Legal Query: " + query[:30] + "...", "PASS", message, data)
        else:
            print_error("❌ Query failed: " + message)
            results.add_result("Legal Query: " + query[:30] + "...", "FAIL", message)
        time.sleep(0.5)

def test_market_intelligence(client):
    print_header("Testing Market Intelligence")
    
    endpoints = [
        ("/market-intelligence/trends", "Market Trends"),
        ("/market-intelligence/competitors", "Competitors")
    ]
    
    for endpoint, name in endpoints:
        print_info("Fetching " + name + "...")
        success, message, data = client.test_endpoint("GET", endpoint)
        if success and data:
            print_success("✅ " + name + " data fetched")
            results.add_result("Market: " + name, "PASS", message, data)
        else:
            print_error("❌ " + name + " failed: " + message)
            results.add_result("Market: " + name, "FAIL", message)

# ===================================================================
# Main Test Runner
# ===================================================================
def run_all_tests():
    print_header("🚀 LEXSARTHI v4.0 - COMPLETE AGENT TEST SUITE")
    print_info("Start Time: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print_info("API Base: " + API_BASE)
    print_info("Total Agents to Test: " + str(len(ALL_AGENTS)))
    
    client = APIClient(API_BASE)
    
    if not client.login(TEST_EMAIL, TEST_PASSWORD):
        print_warning("Login failed, trying registration...")
        if not client.register(TEST_EMAIL, TEST_USERNAME, TEST_PASSWORD):
            print_error("Failed to authenticate. Please ensure API is running.")
            return
    
    print_header("🔍 RUNNING TESTS")
    
    test_health(client)
    test_root(client)
    test_list_agents(client)
    test_domain_scan(client)
    test_legal_query(client)
    test_market_intelligence(client)
    test_all_agents(client)
    
    print_header("📊 TEST SUMMARY")
    print("")
    print("Total Tests: " + str(results.total))
    print("✅ Passed: " + str(results.passed))
    print("❌ Failed: " + str(results.failed))
    print("")
    
    if results.failed == 0:
        print("🎉 ALL TESTS PASSED! LexSarthi v4.0 is fully operational!")
    else:
        print("⚠️ " + str(results.failed) + " tests failed. Please check the errors above.")
    
    print_info("End Time: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 80)

# ===================================================================
# Main Entry Point
# ===================================================================
if __name__ == "__main__":
    run_all_tests()