#!/bin/bash

# Test script for job results endpoint
# This script checks job status first, then retrieves results if completed

API_BASE="http://localhost:5050/api/v1"
JOB_ID="c133b980-5395-4c37-b81d-210da13d190c"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Job Results Test Script ===${NC}"
echo ""
echo "Testing job ID: ${JOB_ID}"
echo ""

# Step 1: Check job status
echo -e "${YELLOW}Step 1: Checking job status...${NC}"

STATUS_RESPONSE=$(curl -s "${API_BASE}/status/${JOB_ID}")

echo ""
echo -e "${GREEN}=== Job Status Response ===${NC}"
echo "$STATUS_RESPONSE" | python -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"

# Extract status from response
STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

echo ""
echo -e "${YELLOW}Job Status: ${STATUS}${NC}"

# Step 2: Only get results if job is completed
if [ "$STATUS" = "completed" ]; then
    echo ""
    echo -e "${GREEN}Job is completed. Retrieving results...${NC}"
    echo ""

    RESULT_RESPONSE=$(curl -s "${API_BASE}/result/${JOB_ID}")

    echo -e "${GREEN}=== Job Result Response ===${NC}"
    echo "$RESULT_RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESULT_RESPONSE"

    echo ""
    echo -e "${YELLOW}=== Checking for report_content field ===${NC}"

    if echo "$RESULT_RESPONSE" | grep -q '"report_content"'; then
        echo -e "${GREEN}report_content field is present${NC}"
        echo ""
        echo "Report content:"
        echo "$RESULT_RESPONSE" | python -c "import sys, json; data = json.load(sys.stdin); print(json.dumps(data.get('report_content', {}), indent=2))" 2>/dev/null
    else
        echo -e "${RED}report_content field is MISSING${NC}"
    fi

    echo ""
    echo -e "${YELLOW}=== Checking for messages_content field ===${NC}"

    if echo "$RESULT_RESPONSE" | grep -q '"messages_content"'; then
        echo -e "${GREEN}messages_content field is present${NC}"
        echo ""
        echo "Messages content (first 500 chars):"
        echo "$RESULT_RESPONSE" | python -c "import sys, json; data = json.load(sys.stdin); msg = data.get('messages_content', ''); print(msg[:500] if msg else 'Empty')" 2>/dev/null
    else
        echo -e "${RED}messages_content field is MISSING${NC}"
    fi
else
    echo -e "${RED}Job is not completed (status: ${STATUS}). Skipping result retrieval.${NC}"
fi

echo ""
echo -e "${GREEN}=== Test Complete ===${NC}"
