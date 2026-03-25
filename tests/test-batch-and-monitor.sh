#!/bin/bash

# Merged test script: sends batch requests and monitors job status
# Sends two requests and monitors both jobs with 5-minute intervals

API_BASE="http://localhost:5050/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Batch Process and Job Monitoring Script ===${NC}"
echo ""

# Step 1: Send first request
echo -e "${BLUE}Step 1: Sending first request...${NC}"
RESPONSE1=$(curl -s -X POST "${API_BASE}/process" \
  -F 'image=@data/input/creative_2.png' \
  -F 'recommendations=[{"id":"rec-1","title":"Deepen Emotional Narrative with Lifestyle Context","description":"Refine product image styling and decorative elements to communicate a desired lifestyle or emotional state—such as freedom, discovery, or personal expression—rather than surface-level fun. This elevates emotional resonance and strengthens the motivational hook driving conversion action.","type":"colour_mood"}]' \
  -F 'brand_guidelines={"protected_regions":["Do not modify or remove the brand logo"],"aspect_ratio":"Maintain original aspect ratio (636x1063)"}')

echo -e "${GREEN}=== First Request Response ===${NC}"
echo "$RESPONSE1" | python -m json.tool 2>/dev/null || echo "$RESPONSE1"

# Extract job ID from first response
JOB_ID1=$(echo "$RESPONSE1" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
if [ -z "$JOB_ID1" ]; then
    JOB_ID1=$(echo "$RESPONSE1" | grep -o '"job_id": "[^"]*"' | cut -d'"' -f4)
fi

echo ""
if [ -n "$JOB_ID1" ]; then
    echo -e "${GREEN}First job ID: ${JOB_ID1}${NC}"
else
    echo -e "${RED}Failed to extract job ID from first request${NC}"
fi

echo ""

# Step 2: Send second request
echo -e "${BLUE}Step 2: Sending second request...${NC}"
RESPONSE2=$(curl -s -X POST "${API_BASE}/process" \
  -F 'image=@data/input/creative_1.png' \
  -F 'recommendations=[{"id":"rec-1","title":"Strengthen Headline Impact","description":"Add visual punch to the headline through enhanced color contrast, a soft gradient backdrop, or a geometric shape—without increasing its physical size. The moderate attention on the discount message suggests it needs more visual emphasis to register urgency and value immediately.","type":"contrast_salience"}]' \
  -F 'brand_guidelines={"protected_regions":["Do not modify or remove the brand logo"],"aspect_ratio":"Maintain original aspect ratio (1572x1720)"}')

echo -e "${GREEN}=== Second Request Response ===${NC}"
echo "$RESPONSE2" | python -m json.tool 2>/dev/null || echo "$RESPONSE2"

# Extract job ID from second response
JOB_ID2=$(echo "$RESPONSE2" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
if [ -z "$JOB_ID2" ]; then
    JOB_ID2=$(echo "$RESPONSE2" | grep -o '"job_id": "[^"]*"' | cut -d'"' -f4)
fi

echo ""
if [ -n "$JOB_ID2" ]; then
    echo -e "${GREEN}Second job ID: ${JOB_ID2}${NC}"
else
    echo -e "${RED}Failed to extract job ID from second request${NC}"
fi

echo ""

# Check if we have both job IDs
if [ -z "$JOB_ID1" ] || [ -z "$JOB_ID2" ]; then
    echo -e "${RED}Error: Could not extract both job IDs. Exiting.${NC}"
    exit 1
fi

# Step 3: Monitor job status with 5-minute intervals
echo -e "${YELLOW}=== Monitoring Job Status ===${NC}"
echo "Monitoring jobs with 5-minute intervals..."
echo "Job 1: ${JOB_ID1}"
echo "Job 2: ${JOB_ID2}"
echo ""

# Track completion status
JOB1_COMPLETED=false
JOB2_COMPLETED=false
MAX_ITERATIONS=12  # 5 minutes * 12 = 60 minutes max

for i in $(seq 1 $MAX_ITERATIONS); do
    echo -e "${YELLOW}--- Check ${i} at $(date) ---${NC}"
    echo ""
    
    # Check Job 1 status
    if [ "$JOB1_COMPLETED" = false ]; then
        echo -e "${BLUE}Checking status for Job 1 (${JOB_ID1})...${NC}"
        STATUS_RESPONSE1=$(curl -s "${API_BASE}/status/${JOB_ID1}")
        STATUS1=$(echo "$STATUS_RESPONSE1" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ -z "$STATUS1" ]; then
            STATUS1=$(echo "$STATUS_RESPONSE1" | grep -o '"status": "[^"]*"' | cut -d'"' -f4)
        fi
        
        echo "Job 1 Status: ${STATUS1}"
        
        if [ "$STATUS1" = "completed" ]; then
            JOB1_COMPLETED=true
            echo -e "${GREEN}Job 1 completed! Retrieving results...${NC}"
            echo ""
            
            RESULT_RESPONSE1=$(curl -s "${API_BASE}/result/${JOB_ID1}")
            echo -e "${GREEN}=== Job 1 Result Response ===${NC}"
            echo "$RESULT_RESPONSE1" | python -m json.tool 2>/dev/null || echo "$RESULT_RESPONSE1"
            echo ""
        elif [ "$STATUS1" = "failed" ] || [ "$STATUS1" = "error" ]; then
            JOB1_COMPLETED=true
            echo -e "${RED}Job 1 failed!${NC}"
            echo -e "${RED}=== Job 1 Error Details ===${NC}"
            echo "$STATUS_RESPONSE1" | python -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE1"
            echo ""
        else
            echo -e "${YELLOW}Job 1 still processing (status: ${STATUS1})...${NC}"
        fi
    fi
    
    echo ""
    
    # Check Job 2 status
    if [ "$JOB2_COMPLETED" = false ]; then
        echo -e "${BLUE}Checking status for Job 2 (${JOB_ID2})...${NC}"
        STATUS_RESPONSE2=$(curl -s "${API_BASE}/status/${JOB_ID2}")
        STATUS2=$(echo "$STATUS_RESPONSE2" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ -z "$STATUS2" ]; then
            STATUS2=$(echo "$STATUS_RESPONSE2" | grep -o '"status": "[^"]*"' | cut -d'"' -f4)
        fi
        
        echo "Job 2 Status: ${STATUS2}"
        
        if [ "$STATUS2" = "completed" ]; then
            JOB2_COMPLETED=true
            echo -e "${GREEN}Job 2 completed! Retrieving results...${NC}"
            echo ""
            
            RESULT_RESPONSE2=$(curl -s "${API_BASE}/result/${JOB_ID2}")
            echo -e "${GREEN}=== Job 2 Result Response ===${NC}"
            echo "$RESULT_RESPONSE2" | python -m json.tool 2>/dev/null || echo "$RESULT_RESPONSE2"
            echo ""
        elif [ "$STATUS2" = "failed" ] || [ "$STATUS2" = "error" ]; then
            JOB2_COMPLETED=true
            echo -e "${RED}Job 2 failed!${NC}"
            echo -e "${RED}=== Job 2 Error Details ===${NC}"
            echo "$STATUS_RESPONSE2" | python -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE2"
            echo ""
        else
            echo -e "${YELLOW}Job 2 still processing (status: ${STATUS2})...${NC}"
        fi
    fi
    
    # Check if both jobs are done
    if [ "$JOB1_COMPLETED" = true ] && [ "$JOB2_COMPLETED" = true ]; then
        echo -e "${GREEN}=== All jobs completed ===${NC}"
        break
    fi
    
    echo ""
    echo -e "${YELLOW}Waiting 5 minutes before next check...${NC}"
    sleep 300
done

# Final summary
echo ""
echo -e "${GREEN}=== Monitoring Complete ===${NC}"
echo ""

if [ "$JOB1_COMPLETED" = true ]; then
    echo -e "${GREEN}Job 1 (${JOB_ID1}): Completed${NC}"
else
    echo -e "${YELLOW}Job 1 (${JOB_ID1}): Still processing after maximum time${NC}"
fi

if [ "$JOB2_COMPLETED" = true ]; then
    echo -e "${GREEN}Job 2 (${JOB_ID2}): Completed${NC}"
else
    echo -e "${YELLOW}Job 2 (${JOB_ID2}): Still processing after maximum time${NC}"
fi

echo ""
echo -e "${GREEN}=== Script Complete ===${NC}"
