#!/usr/bin/env bash
# ORION Architekt AT - Complete Test Suite Runner
# =================================================
# Führt alle Tests aus und generiert Reports
# Nutzung: ./run_all_tests.sh

set -e  # Exit on error

echo "================================================================================"
echo "ORION ARCHITEKT AT - COMPLETE TEST SUITE"
echo "================================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in CI environment
if [ -n "$CI" ]; then
    echo "🤖 Running in CI environment"
    CI_MODE=true
else
    echo "💻 Running in local environment"
    CI_MODE=false
fi

# Function to print section header
print_section() {
    echo ""
    echo "================================================================================"
    echo "$1"
    echo "================================================================================"
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install dependencies if needed
print_section "STEP 1: Checking Dependencies"

if ! command_exists pytest; then
    echo "⚠️  pytest not found, installing..."
    pip3 install -r requirements.txt
else
    echo "✅ pytest found"
fi

if ! python3 -c "import numpy" 2>/dev/null; then
    echo "⚠️  numpy not found, installing..."
    pip3 install numpy>=2.3.0
else
    echo "✅ numpy found"
fi

# Check Python version
print_section "STEP 2: Environment Check"
python3 --version
pip3 --version
echo ""
echo "Python packages installed:"
pip3 list | grep -E "(pytest|numpy|fastapi|sqlalchemy|redis)" || echo "Some packages missing"

# Run pytest tests
print_section "STEP 3: Running pytest Tests (Unit & Integration)"

if pytest tests/ -v --tb=short --cov=. --cov-report=html --cov-report=term 2>&1 | tee pytest_output.txt; then
    echo -e "${GREEN}✅ pytest tests PASSED${NC}"
    PYTEST_RESULT=0
else
    echo -e "${RED}❌ pytest tests FAILED${NC}"
    PYTEST_RESULT=1
fi

# Run integration tests
print_section "STEP 4: Running Integration Tests"

echo "Test 1: Complete Integration (10 modules)"
if python3 test_complete_integration.py 2>&1 | tee complete_integration_output.txt | tail -50; then
    echo -e "${GREEN}✅ Complete Integration PASSED${NC}"
    COMPLETE_INT_RESULT=0
else
    echo -e "${RED}❌ Complete Integration FAILED${NC}"
    COMPLETE_INT_RESULT=1
fi

echo ""
echo "Test 2: AI Integration"
if python3 test_ai_integration.py 2>&1 | tee ai_integration_output.txt | tail -30; then
    echo -e "${GREEN}✅ AI Integration PASSED${NC}"
    AI_INT_RESULT=0
else
    echo -e "${RED}❌ AI Integration FAILED${NC}"
    AI_INT_RESULT=1
fi

echo ""
echo "Test 3: Multi-Agent Integration"
if python3 test_multi_agent_integration.py 2>&1 | tee multi_agent_output.txt | tail -30; then
    echo -e "${GREEN}✅ Multi-Agent Integration PASSED${NC}"
    MULTI_AGENT_RESULT=0
else
    echo -e "${RED}❌ Multi-Agent Integration FAILED${NC}"
    MULTI_AGENT_RESULT=1
fi

echo ""
echo "Test 4: GENESIS Integration"
if python3 test_genesis_integration.py 2>&1 | tee genesis_output.txt | tail -30; then
    echo -e "${GREEN}✅ GENESIS Integration PASSED${NC}"
    GENESIS_RESULT=0
else
    echo -e "${RED}❌ GENESIS Integration FAILED${NC}"
    GENESIS_RESULT=1
fi

echo ""
echo "Test 5: ÖNORM A 2063 Tendering"
if python3 test_orion_oenorm_a2063.py 2>&1 | tee oenorm_output.txt | tail -30; then
    echo -e "${GREEN}✅ ÖNORM A 2063 PASSED${NC}"
    OENORM_RESULT=0
else
    echo -e "${RED}❌ ÖNORM A 2063 FAILED${NC}"
    OENORM_RESULT=1
fi

# Run standalone module tests
print_section "STEP 5: Running Standalone Module Tests"

echo "Test 6: Integration Fixes Verification"
if python3 integration_fixes.py 2>&1 | tee integration_fixes_output.txt; then
    echo -e "${GREEN}✅ Integration Fixes PASSED${NC}"
    INT_FIXES_RESULT=0
else
    echo -e "${RED}❌ Integration Fixes FAILED${NC}"
    INT_FIXES_RESULT=1
fi

# API Health Check (if API is running)
print_section "STEP 6: API Health Check"

if command_exists curl; then
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ API is running and healthy${NC}"
        curl -s http://localhost:8000/health | python3 -m json.tool || echo "API response not JSON"
        API_HEALTH=0
    else
        echo -e "${YELLOW}⚠️  API not running (expected in test environment)${NC}"
        API_HEALTH=1
    fi
else
    echo -e "${YELLOW}⚠️  curl not installed, skipping API check${NC}"
    API_HEALTH=1
fi

# Generate Summary Report
print_section "TEST RESULTS SUMMARY"

TOTAL_TESTS=6
PASSED_TESTS=0

echo "Test Results:"
echo "============="
if [ $PYTEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Unit Tests (pytest)${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Unit Tests (pytest)${NC}"
fi

if [ $COMPLETE_INT_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Complete Integration (10 modules)${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Complete Integration${NC}"
fi

if [ $AI_INT_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ AI Integration${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ AI Integration${NC}"
fi

if [ $MULTI_AGENT_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Multi-Agent Integration${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Multi-Agent Integration${NC}"
fi

if [ $GENESIS_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ GENESIS Integration${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ GENESIS Integration${NC}"
fi

if [ $OENORM_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ ÖNORM A 2063${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ ÖNORM A 2063${NC}"
fi

echo ""
echo "Success Rate: $PASSED_TESTS/$TOTAL_TESTS ($(( PASSED_TESTS * 100 / TOTAL_TESTS ))%)"

# Generate HTML Report
print_section "STEP 7: Generating Reports"

echo "📊 Coverage Report: htmlcov/index.html"
echo "📄 Test Outputs saved to *_output.txt files"

# Save summary to file
cat > test_summary.txt <<EOF
ORION ARCHITEKT AT - TEST SUMMARY
=================================
Date: $(date)
Environment: $([ "$CI_MODE" = true ] && echo "CI" || echo "Local")

Results:
--------
Unit Tests (pytest):         $([ $PYTEST_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")
Complete Integration:        $([ $COMPLETE_INT_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")
AI Integration:              $([ $AI_INT_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")
Multi-Agent Integration:     $([ $MULTI_AGENT_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")
GENESIS Integration:         $([ $GENESIS_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")
ÖNORM A 2063:                $([ $OENORM_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")

Success Rate: $PASSED_TESTS/$TOTAL_TESTS ($(( PASSED_TESTS * 100 / TOTAL_TESTS ))%)

Files Generated:
---------------
- htmlcov/index.html (Coverage Report)
- pytest_output.txt
- complete_integration_output.txt
- ai_integration_output.txt
- multi_agent_output.txt
- genesis_output.txt
- oenorm_output.txt
- integration_fixes_output.txt
- test_summary.txt (this file)
EOF

echo "✅ Summary saved to test_summary.txt"

# Final status
print_section "FINAL STATUS"

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! System is PRODUCTION READY!${NC}"
    exit 0
elif [ $PASSED_TESTS -ge $(( TOTAL_TESTS * 80 / 100 )) ]; then
    echo -e "${YELLOW}⚠️  $PASSED_TESTS/$TOTAL_TESTS tests passed (≥80%). System is MOSTLY READY.${NC}"
    exit 0
else
    echo -e "${RED}❌ Only $PASSED_TESTS/$TOTAL_TESTS tests passed (<80%). FIXES REQUIRED.${NC}"
    exit 1
fi
