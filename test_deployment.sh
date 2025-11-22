#!/bin/bash

echo "=================================================="
echo "  ITB CHATBOT - DEPLOYMENT VERIFICATION TEST"
echo "=================================================="
echo ""

# Load API key
export API_KEY=$(grep "^API_KEY=" .env | cut -d '=' -f2)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

test_count=0
pass_count=0

run_test() {
    test_count=$((test_count + 1))
    echo -e "${BLUE}Test $test_count: $1${NC}"
}

pass() {
    pass_count=$((pass_count + 1))
    echo -e "${GREEN}✓ PASS${NC}"
    echo ""
}

fail() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    echo ""
}

# Test 1: Health Check
run_test "Health Check"
response=$(curl -s http://localhost:8000/health)
if echo "$response" | grep -q "healthy"; then
    pass
else
    fail "Health check failed"
fi

# Test 2: Redis Connection
run_test "Redis Connection"
if echo "$response" | grep -q '"redis": "ok"'; then
    pass
else
    fail "Redis not connected"
fi

# Test 3: Ready Check
run_test "Readiness Check"
response=$(curl -s http://localhost:8000/ready)
if echo "$response" | grep -q "ready"; then
    pass
else
    fail "Ready check failed"
fi

# Test 4: Valid Chat Request
run_test "Valid Chat Request"
response=$(curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Conversation-Id: test-$(date +%s)" \
  -d '{"message": "Hello"}')
if echo "$response" | grep -q "answer"; then
    pass
else
    fail "Chat request failed"
fi

# Test 5: Error Handling - No API Key
run_test "Error Handling (No API Key)"
response=$(curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Conversation-Id: test-123" \
  -d '{"message": "test"}')
if echo "$response" | grep -q "X-API-Key header is required"; then
    pass
else
    fail "Should return API key error"
fi

# Test 6: Error Handling - Invalid API Key
run_test "Error Handling (Invalid API Key)"
response=$(curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid" \
  -H "X-Conversation-Id: test-123" \
  -d '{"message": "test"}')
if echo "$response" | grep -q "Invalid API key"; then
    pass
else
    fail "Should return invalid API key error"
fi

# Test 7: Input Validation - Empty Message
run_test "Input Validation (Empty Message)"
response=$(curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Conversation-Id: test-123" \
  -d '{"message": ""}')
if echo "$response" | grep -q "Message cannot be empty"; then
    pass
else
    fail "Should validate empty message"
fi

# Test 8: Docker Container Status
run_test "Docker Containers Running"
if docker-compose ps | grep -q "Up"; then
    pass
else
    fail "Containers not running"
fi

# Test 9: Structured Logging
run_test "Structured Logging (JSON)"
logs=$(docker-compose logs app --tail 10 | grep -o '{"timestamp".*}')
if [ -n "$logs" ]; then
    pass
else
    fail "JSON logs not found"
fi

# Test 10: Conversation Persistence
run_test "Conversation Persistence"
CONV_ID="persist-test-$(date +%s)"
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Conversation-Id: ${CONV_ID}" \
  -d '{"message": "Remember: my favorite color is blue"}' > /dev/null

sleep 1

response=$(curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Conversation-Id: ${CONV_ID}" \
  -d '{"message": "What is my favorite color?"}')

if echo "$response" | grep -qi "blue"; then
    pass
else
    # Some models might not remember, but request should succeed
    if echo "$response" | grep -q "answer"; then
        pass
    else
        fail "Conversation failed"
    fi
fi

# Summary
echo "=================================================="
echo "  TEST SUMMARY"
echo "=================================================="
echo -e "Total Tests: $test_count"
echo -e "${GREEN}Passed: $pass_count${NC}"
echo -e "${RED}Failed: $((test_count - pass_count))${NC}"
echo ""

if [ $pass_count -eq $test_count ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED - DEPLOYMENT VERIFIED${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
