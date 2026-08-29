#!/bin/bash

# ============================================
# UNKNOWN VERDICT v43.0 – COMPLETE TEST SUITE
# ============================================

BASE_URL="${1:-http://localhost:7860}"
TOKEN=""
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
PASS=0
FAIL=0
TOTAL=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        UNKNOWN VERDICT v43.0 – COMPLETE TEST SUITE           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Testing: ${BASE_URL}"
echo ""

# Helper functions
function test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected=$5
    local url="${BASE_URL}${endpoint}"
    local response=""
    local status=0

    echo -n "  ➜ ${name} ... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" -H "Content-Type: application/json" "$url" 2>/dev/null)
        status=${response: -3}
        body=${response%???}
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null)
        status=${response: -3}
        body=${response%???}
    fi

    TOTAL=$((TOTAL + 1))
    if [ "$status" -eq "$expected" ] || [ "$status" -eq 200 ] && [ "$expected" -eq 200 ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $status)"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $status, expected $expected)"
        FAIL=$((FAIL + 1))
        if [ ! -z "$body" ] && [ ${#body} -lt 200 ]; then
            echo "    Response: $body"
        fi
    fi
}

function test_json() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local key=$5
    local expected_value=$6
    local url="${BASE_URL}${endpoint}"
    local response=""
    local status=0

    echo -n "  ➜ ${name} ... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" -H "Content-Type: application/json" "$url" 2>/dev/null)
        status=${response: -3}
        body=${response%???}
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null)
        status=${response: -3}
        body=${response%???}
    fi

    TOTAL=$((TOTAL + 1))
    if [ "$status" -eq 200 ] || [ "$status" -eq 201 ]; then
        # Check for key in JSON
        if echo "$body" | grep -q "\"$key\""; then
            echo -e "${GREEN}✓ PASS${NC} (found '$key')"
            PASS=$((PASS + 1))
        else
            echo -e "${RED}✗ FAIL${NC} (key '$key' not found)"
            FAIL=$((FAIL + 1))
            echo "    Response: ${body:0:200}"
        fi
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $status)"
        FAIL=$((FAIL + 1))
    fi
}

# ============================================
# SECTION 1: CORE SYSTEM
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}📡 1. CORE SYSTEM TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

test_endpoint "Health Check" "GET" "/health" "" 200
test_endpoint "Root Status" "GET" "/" "" 200
test_endpoint "API Docs" "GET" "/docs" "" 200
test_endpoint "OpenAPI JSON" "GET" "/openapi.json" "" 200
test_json "System Status" "GET" "/" "" "status" "operational"
test_json "Health Status" "GET" "/health" "" "status" "operational"

# ============================================
# SECTION 2: CHAT & LLM
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}💬 2. CHAT & LLM TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

test_endpoint "Chat Endpoint" "POST" "/chat" '{"message":"What is the Indian Contract Act?"}' 200
test_json "Chat Response" "POST" "/chat" '{"message":"Test query"}' "response" ""
test_endpoint "Empty Chat" "POST" "/chat" '{"message":""}' 400

# ============================================
# SECTION 3: RAG (Retrieval-Augmented Generation)
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}📚 3. RAG TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

test_endpoint "RAG Search" "POST" "/rag/search" '{"query":"Supreme Court privacy", "top_k":5}' 200
test_json "RAG Search Result" "POST" "/rag/search" '{"query":"contract breach"}' "results" ""
test_endpoint "RAG Empty Query" "POST" "/rag/search" '{"query":""}' 400

# ============================================
# SECTION 4: AGENTS
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}🤖 4. AGENTS TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

test_endpoint "List Agents" "GET" "/agents" "" 200
test_json "Agents Count" "GET" "/agents" "" "count" ""
test_endpoint "Agent Invocation" "POST" "/agent/ComplianceAgent" '{"query":"Test query"}' 200
test_endpoint "Agent Not Found" "POST" "/agent/NonexistentAgent" '{"query":"Test"}' 404

# ============================================
# SECTION 5: MOAT INTELLIGENCE
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}🔮 5. MOAT TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

test_endpoint "Moat Status" "GET" "/api/moat/status" "" 200
test_json "Moat Status JSON" "GET" "/api/moat/status" "" "status" "operational"
test_endpoint "Moat Evolution Record" "POST" "/api/moat/evolution/record" '{"query":"Test", "response":"Test response", "feedback":"good"}' 200
test_endpoint "Moat IRAC Reason" "POST" "/api/moat/irac/reason" '{"issue":"Contract breach", "jurisdiction":"India"}' 200

# ============================================
# SECTION 6: THIRD EYE
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}👁️ 6. THIRD EYE TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

test_endpoint "Third Eye Status" "GET" "/third-eye" "" 200
test_json "Third Eye JSON" "GET" "/third-eye" "" "status" "active"

# ============================================
# SECTION 7: SECURITY
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}🔒 7. SECURITY TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

# Test .env security (should be blocked)
test_endpoint "Env File Protection" "GET" "/.env" "" 404
test_endpoint "Env Prod Protection" "GET" "/.env.production" "" 404
test_endpoint "Secrets Protection" "GET" "/.streamlit/secrets.toml" "" 404

# ============================================
# SECTION 8: DATABASE (via status)
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}🗄️ 8. DATABASE TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

test_json "DB Status" "GET" "/health" "" "offline_ready" ""

# ============================================
# SECTION 9: PERFORMANCE (optional)
# ============================================
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}⚡ 9. PERFORMANCE TESTS${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────${NC}"

# Quick latency test
echo -n "  ➜ Response Time (/health) ... "
START_TIME=$(date +%s%N)
curl -s -o /dev/null "${BASE_URL}/health"
END_TIME=$(date +%s%N)
DURATION=$((($END_TIME - $START_TIME)/1000000))
TOTAL=$((TOTAL + 1))
if [ $DURATION -lt 1000 ]; then
    echo -e "${GREEN}✓ PASS${NC} (${DURATION}ms)"
    PASS=$((PASS + 1))
else
    echo -e "${YELLOW}⚠ SLOW${NC} (${DURATION}ms)"
    FAIL=$((FAIL + 1))
fi

# ============================================
# SECTION 10: SUMMARY
# ============================================
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                       TEST SUMMARY                             ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ✅ Passed: ${GREEN}${PASS}${NC}"
echo -e "  ❌ Failed: ${RED}${FAIL}${NC}"
echo -e "  📊 Total:  ${TOTAL}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! Unknown Verdict v43.0 is operational.${NC}"
else
    echo -e "${YELLOW}⚠️ ${FAIL} test(s) failed. Check the logs above.${NC}"
fi

echo ""
echo -e "📍 Live: ${BASE_URL}"
echo -e "📚 Docs: ${BASE_URL}/docs"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"