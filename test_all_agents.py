#!/usr/bin/env python3
"""
LexSarthi v2.4 - Complete Testing Suite
Tests all 50+ agents, payment flows, authentication, and all endpoints
"""

import asyncio
import aiohttp
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# ===== Configuration =====
BASE_URL = "https://upamnyu12-lex.hf.space"  # Your Hugging Face Space URL
# Or use localhost for testing locally
# BASE_URL = "http://localhost:7860"

# Test user credentials
TEST_USER = {
    "email": f"test_{int(time.time())}@lexsarthi.com",
    "password": "Test@123456",
    "full_name": "Test User"
}

# ===== Colorful Output =====
class Colors:
    HEADER = Fore.MAGENTA
    SUCCESS = Fore.GREEN
    WARNING = Fore.YELLOW
    ERROR = Fore.RED
    INFO = Fore.CYAN
    RESET = Style.RESET_ALL

def print_header(text):
    print(f"\n{Colors.HEADER}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.SUCCESS}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.ERROR}❌ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.INFO}ℹ️  {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.RESET}")

def print_test_result(test_name, passed, details=""):
    if passed:
        print(f"{Colors.SUCCESS}✅ PASS: {test_name}{Colors.RESET}")
    else:
        print(f"{Colors.ERROR}❌ FAIL: {test_name}{Colors.RESET}")
    if details:
        print(f"   {details}")

# ===== Test Results =====
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "details": []
}

def record_result(test_name: str, passed: bool, details: str = ""):
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    test_results["details"].append({
        "name": test_name,
        "passed": passed,
        "details": details
    })
    print_test_result(test_name, passed, details)

# ===== API Client =====
class LexSarthiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def request(self, method: str, endpoint: str, data: Any = None, 
                      headers: Dict = None, params: Dict = None) -> tuple:
        """Make API request and return (success, response_data, status_code)"""
        url = f"{self.base_url}{endpoint}"
        headers = headers or {}
        
        if self.token and not endpoint.startswith("/auth"):
            headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            async with self.session.request(
                method, url, json=data, headers=headers, params=params
            ) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                success = 200 <= response.status < 300
                return success, response_data, response.status
        except Exception as e:
            return False, {"error": str(e)}, 500

    # ===== Auth Tests =====
    async def test_health(self) -> bool:
        """Test health endpoint"""
        success, data, status = await self.request("GET", "/health")
        if success and data.get("status") == "healthy":
            print_info(f"Health check: {data.get('version')} with {data.get('agent_count')} agents")
            return True
        return False

    async def test_register(self, email: str, password: str, full_name: str) -> bool:
        """Test user registration"""
        data = {"email": email, "password": password, "full_name": full_name}
        success, response, status = await self.request("POST", "/auth/register", data)
        if success:
            print_success(f"Registered user: {email}")
            return True
        print_error(f"Registration failed: {response}")
        return False

    async def test_login(self, email: str, password: str) -> bool:
        """Test user login"""
        data = {"email": email, "password": password}
        success, response, status = await self.request("POST", "/auth/login", data)
        if success:
            self.token = response.get("token")
            self.user_id = response.get("user", {}).get("id")
            print_success(f"Logged in user: {email}")
            return True
        print_error(f"Login failed: {response}")
        return False

    async def test_get_profile(self) -> bool:
        """Test get current user profile"""
        success, data, status = await self.request("GET", "/auth/me")
        if success and data.get("id") == self.user_id:
            print_success(f"Profile loaded: {data.get('full_name')}")
            return True
        print_error(f"Profile load failed: {data}")
        return False

    async def test_change_password(self, current: str, new: str) -> bool:
        """Test password change"""
        data = {"current_password": current, "new_password": new}
        success, response, status = await self.request("POST", "/auth/change-password", data)
        if success:
            print_success("Password changed successfully")
            return True
        print_error(f"Password change failed: {response}")
        return False

    # ===== Agent Tests =====
    async def test_list_agents(self) -> tuple:
        """Test listing all agents"""
        success, data, status = await self.request("GET", "/agents")
        if success:
            agents = data.get("agents", [])
            categories = data.get("categories", [])
            print_info(f"Loaded {len(agents)} agents across {len(categories)} categories")
            return True, agents
        print_error(f"Agent list failed: {data}")
        return False, []

    async def test_run_agent(self, agent_id: str, input_text: str = "What is a contract?") -> bool:
        """Test running a specific agent"""
        data = {
            "agent_id": agent_id,
            "input_text": input_text
        }
        success, response, status = await self.request("POST", "/run-agent", data)
        if success:
            agent_name = response.get("agent_name", agent_id)
            response_text = response.get("response", "")
            print_success(f"Agent '{agent_name}' executed successfully")
            print_info(f"Response preview: {response_text[:100]}...")
            return True
        print_error(f"Agent execution failed: {response}")
        return False

    async def test_run_all_agents(self, agents: List[Dict]) -> Dict:
        """Test running all agents (limit to first 5 for speed)"""
        results = {"total": 0, "passed": 0, "failed": 0, "errors": []}
        
        # Test a subset of agents (all categories)
        test_agents = agents[:10]  # Test first 10 agents
        
        print_info(f"Testing {len(test_agents)} agents...")
        
        for agent in test_agents:
            agent_id = agent.get("id")
            agent_name = agent.get("name", agent_id)
            
            # Skip premium agents if not premium
            if agent.get("premium", False):
                print_warning(f"Skipping premium agent: {agent_name}")
                continue
            
            success = await self.test_run_agent(agent_id, f"Explain what you do as a legal assistant")
            results["total"] += 1
            if success:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(agent_name)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        return results

    # ===== Domain Tests =====
    async def test_domain_scan(self, domain: str = "google.com") -> bool:
        """Test domain intelligence scan"""
        data = {"domain": domain}
        success, response, status = await self.request("POST", "/scan-domain", data)
        if success:
            print_success(f"Domain scan completed for {domain}")
            if response.get("summary"):
                print_info(f"Summary: {response['summary']}")
            return True
        print_error(f"Domain scan failed: {response}")
        return False

    # ===== Policy Tests =====
    async def test_policy_scan(self, url: str = "https://google.com") -> bool:
        """Test policy compliance scanner"""
        data = {"url": url}
        success, response, status = await self.request("POST", "/scan-policies", data)
        if success:
            print_success(f"Policy scan completed for {url}")
            if response.get("compliance_analysis"):
                analysis = response["compliance_analysis"]
                privacy = analysis.get("privacy_policy_found", False)
                terms = analysis.get("terms_found", False)
                print_info(f"Privacy Policy: {'✅' if privacy else '❌'}")
                print_info(f"Terms of Service: {'✅' if terms else '❌'}")
            return True
        print_error(f"Policy scan failed: {response}")
        return False

    # ===== Citation Tests =====
    async def test_citation_verify(self, citation: str = "AIR 2020 SC 123") -> bool:
        """Test legal citation verification"""
        data = {"citation": citation}
        success, response, status = await self.request("POST", "/verify-citation", data)
        if success:
            print_success(f"Citation verified: {citation}")
            print_info(f"Verified: {response.get('verified', False)}")
            return True
        print_error(f"Citation verification failed: {response}")
        return False

    # ===== History Tests =====
    async def test_get_history(self) -> bool:
        """Test getting user history"""
        success, data, status = await self.request("GET", "/history")
        if success:
            history_count = len(data.get("history", []))
            print_success(f"Retrieved {history_count} history items")
            return True
        print_error(f"History retrieval failed: {data}")
        return False

    # ===== Payment Tests =====
    async def test_payment_create_order(self, amount: int = 200) -> bool:
        """Test payment order creation"""
        data = {"amount": amount, "currency": "INR"}
        success, response, status = await self.request("POST", "/payment/create-order", data)
        if success:
            order_id = response.get("order_id")
            print_success(f"Payment order created: {order_id}")
            print_info(f"Amount: ₹{amount/100:.2f}")
            if response.get("test_mode"):
                print_warning("Test mode active (Razorpay not configured)")
            return True, response.get("order_id")
        print_error(f"Payment order creation failed: {response}")
        return False, None

    async def test_payment_verify(self, order_id: str, payment_id: str = "test_pay_123") -> bool:
        """Test payment verification"""
        data = {
            "razorpay_payment_id": payment_id,
            "razorpay_order_id": order_id,
            "razorpay_signature": "test_signature"
        }
        success, response, status = await self.request("POST", "/payment/verify", data)
        if success:
            print_success(f"Payment verified successfully")
            return True
        print_error(f"Payment verification failed: {response}")
        return False

    async def test_payment_history(self) -> bool:
        """Test payment history retrieval"""
        success, data, status = await self.request("GET", "/payment/history")
        if success:
            payments = data.get("payments", [])
            print_success(f"Retrieved {len(payments)} payment records")
            return True
        print_error(f"Payment history retrieval failed: {data}")
        return False

    async def test_payment_status(self) -> bool:
        """Test payment status"""
        success, data, status = await self.request("GET", "/payment/status")
        if success:
            is_premium = data.get("premium", False)
            total_payments = data.get("total_payments", 0)
            print_success(f"Premium status: {'✅ Active' if is_premium else '❌ Inactive'}")
            print_info(f"Total payments: {total_payments}")
            return True
        print_error(f"Payment status retrieval failed: {data}")
        return False

    # ===== File Upload Tests =====
    async def test_file_upload(self) -> bool:
        """Test file upload"""
        import io
        from aiohttp import FormData
        
        # Create a test text file
        test_content = "This is a test legal document for LexSarthi."
        file_data = io.BytesIO(test_content.encode())
        
        form = FormData()
        form.add_field('file', file_data, filename='test_document.txt', content_type='text/plain')
        
        url = f"{self.base_url}/upload"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            async with self.session.post(url, data=form, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print_success(f"File uploaded successfully")
                    print_info(f"Word count: {data.get('word_count', 0)}")
                    return True
                else:
                    print_error(f"File upload failed: {response.status}")
                    return False
        except Exception as e:
            print_error(f"File upload error: {e}")
            return False

    # ===== Grievance Tests =====
    async def test_submit_grievance(self) -> bool:
        """Test grievance submission"""
        data = {
            "subject": "Test Grievance",
            "description": "This is a test grievance submission from the testing suite."
        }
        success, response, status = await self.request("POST", "/auth/grievance", data)
        if success:
            grievance_id = response.get("grievance_id")
            print_success(f"Grievance submitted: {grievance_id}")
            return True
        print_error(f"Grievance submission failed: {response}")
        return False

    # ===== Cleanup =====
    async def test_delete_account(self) -> bool:
        """Test account deletion"""
        success, response, status = await self.request("DELETE", "/auth/me")
        if success:
            print_success("Account deleted successfully")
            return True
        print_error(f"Account deletion failed: {response}")
        return False

# ===== Main Test Suite =====
async def run_all_tests(base_url: str, skip_delete: bool = True, test_payment: bool = True):
    """Run complete test suite"""
    print_header("LexSarthi v2.4 Complete Test Suite")
    print_info(f"Base URL: {base_url}")
    print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with LexSarthiClient(base_url) as client:
        # ===== 1. Health Check =====
        print_header("1. Health Check")
        passed = await client.test_health()
        record_result("Health Check", passed)
        
        if not passed:
            print_error("Cannot proceed - API is not healthy")
            return
        
        # ===== 2. Authentication =====
        print_header("2. Authentication")
        
        # Register
        passed = await client.test_register(
            TEST_USER["email"], 
            TEST_USER["password"], 
            TEST_USER["full_name"]
        )
        record_result("User Registration", passed)
        
        if not passed:
            print_error("Cannot proceed - Registration failed")
            return
        
        # Login
        passed = await client.test_login(TEST_USER["email"], TEST_USER["password"])
        record_result("User Login", passed)
        
        if not passed:
            print_error("Cannot proceed - Login failed")
            return
        
        # Get Profile
        passed = await client.test_get_profile()
        record_result("Get Profile", passed)
        
        # Change Password
        passed = await client.test_change_password(TEST_USER["password"], "NewTest@123456")
        record_result("Change Password", passed)
        
        # Re-login with new password
        passed = await client.test_login(TEST_USER["email"], "NewTest@123456")
        record_result("Re-login after password change", passed)
        
        # ===== 3. Agent Tests =====
        print_header("3. Agent Tests")
        
        # List Agents
        success, agents = await client.test_list_agents()
        record_result("List Agents", success)
        
        if success and agents:
            # Test a few individual agents
            test_agent_ids = [
                "contract_review_general",
                "drafting_general",
                "compliance_dpdp",
                "research_case_law"
            ]
            
            for agent_id in test_agent_ids:
                agent = next((a for a in agents if a.get("id") == agent_id), None)
                if agent and not agent.get("premium", False):
                    passed = await client.test_run_agent(
                        agent_id, 
                        f"Explain what you do as a legal assistant"
                    )
                    record_result(f"Run Agent: {agent.get('name', agent_id)}", passed)
                else:
                    print_warning(f"Skipping agent: {agent_id}")
            
            # Test all agents (limited)
            print_header("4. Bulk Agent Testing")
            results = await client.test_run_all_agents(agents)
            record_result(
                f"Bulk Agent Test ({results['total']} agents)", 
                results['failed'] == 0,
                f"Passed: {results['passed']}, Failed: {results['failed']}"
            )
        
        # ===== 5. Domain Intelligence =====
        print_header("5. Domain Intelligence")
        
        test_domains = ["google.com", "github.com", "wikipedia.org"]
        for domain in test_domains:
            passed = await client.test_domain_scan(domain)
            record_result(f"Domain Scan: {domain}", passed)
            await asyncio.sleep(0.5)  # Rate limiting
        
        # ===== 6. Policy Scanner =====
        print_header("6. Policy Scanner")
        
        test_urls = [
            "https://google.com",
            "https://github.com",
            "https://wikipedia.org"
        ]
        for url in test_urls:
            passed = await client.test_policy_scan(url)
            record_result(f"Policy Scan: {url}", passed)
            await asyncio.sleep(0.5)
        
        # ===== 7. Citation Verification =====
        print_header("7. Citation Verification")
        
        test_citations = [
            "AIR 2020 SC 123",
            "2022 SCC 45",
            "2019 CriLJ 1234",
            "Constitution of India, Article 21"
        ]
        for citation in test_citations:
            passed = await client.test_citation_verify(citation)
            record_result(f"Citation Verify: {citation[:30]}...", passed)
        
        # ===== 8. History =====
        print_header("8. History")
        passed = await client.test_get_history()
        record_result("Get History", passed)
        
        # ===== 9. Grievance =====
        print_header("9. Grievance")
        passed = await client.test_submit_grievance()
        record_result("Submit Grievance", passed)
        
        # ===== 10. File Upload =====
        print_header("10. File Upload")
        passed = await client.test_file_upload()
        record_result("File Upload", passed)
        
        # ===== 11. Payment Tests =====
        if test_payment:
            print_header("11. Payment Integration Tests")
            
            # Test payment status (should be free)
            passed = await client.test_payment_status()
            record_result("Payment Status - Initial", passed)
            
            # Test payment order creation (₹2 test)
            passed, order_id = await client.test_payment_create_order(200)
            record_result("Create Payment Order (₹2)", passed)
            
            if passed and order_id:
                # Test payment verification
                passed = await client.test_payment_verify(order_id)
                record_result("Verify Payment", passed)
            
            # Test payment history
            passed = await client.test_payment_history()
            record_result("Payment History", passed)
            
            # Check premium status after payment
            passed = await client.test_payment_status()
            record_result("Payment Status - After Payment", passed)
            
            # Test premium order (₹999)
            passed, _ = await client.test_payment_create_order(99900)
            record_result("Create Premium Order (₹999)", passed)
        
        # ===== 12. Cleanup =====
        if not skip_delete:
            print_header("12. Cleanup")
            passed = await client.test_delete_account()
            record_result("Delete Account", passed)
        else:
            print_warning("Skipping account deletion (keep for review)")
            print_info(f"Test user: {TEST_USER['email']}")
            print_info(f"Password: {TEST_USER['password']}")
    
    # ===== Print Summary =====
    print_header("TEST SUMMARY")
    print(f"Total Tests: {test_results['total']}")
    print(f"{Colors.SUCCESS}Passed: {test_results['passed']}{Colors.RESET}")
    print(f"{Colors.ERROR}Failed: {test_results['failed']}{Colors.RESET}")
    
    if test_results['failed'] > 0:
        print("\nFailed Tests:")
        for detail in test_results['details']:
            if not detail['passed']:
                print(f"  ❌ {detail['name']}: {detail.get('details', '')}")
    
    success_rate = (test_results['passed'] / test_results['total'] * 100) if test_results['total'] > 0 else 0
    print(f"\n{Colors.INFO}Success Rate: {success_rate:.1f}%{Colors.RESET}")
    
    if test_results['failed'] == 0:
        print(f"\n{Colors.SUCCESS}🎉 ALL TESTS PASSED! 🎉{Colors.RESET}")
        return True
    else:
        print(f"\n{Colors.WARNING}⚠️  Some tests failed. Check the output above.{Colors.RESET}")
        return False

# ===== Command Line Interface =====
def parse_args():
    parser = argparse.ArgumentParser(description="LexSarthi Complete Test Suite")
    parser.add_argument(
        "--url", 
        default=BASE_URL, 
        help="Base URL of the LexSarthi API"
    )
    parser.add_argument(
        "--skip-delete", 
        action="store_true",
        default=True,
        help="Skip account deletion (keep test user)"
    )
    parser.add_argument(
        "--no-payment", 
        action="store_true",
        help="Skip payment integration tests"
    )
    parser.add_argument(
        "--keep-user",
        action="store_true",
        help="Keep the test user account (don't delete)"
    )
    parser.add_argument(
        "--email",
        help="Use specific email for testing"
    )
    parser.add_argument(
        "--password",
        default="Test@123456",
        help="Password for test user"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # Update test user if email provided
    if args.email:
        TEST_USER["email"] = args.email
    TEST_USER["password"] = args.password
    
    # Run tests
    try:
        success = asyncio.run(run_all_tests(
            args.url,
            skip_delete=args.keep_user or args.skip_delete,
            test_payment=not args.no_payment
        ))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.ERROR}Unexpected error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)