#!/bin/bash
set -e

BASE_URL="http://localhost:8888"

echo "=== Testing Task Center API ==="
echo ""

# Test 1: Health check
echo "1. Health check:"
curl -s "${BASE_URL}/health"
echo ""
echo ""

# Generate unique idempotency keys
KEY1="test_key_$(date +%s)_1"
KEY2="test_key_$(date +%s)_2"

# Test 2: Create a task
echo "2. Create task:"
TASK1=$(curl -s -X POST -H "Content-Type: application/json" -d '{
    "type": "example_long_task",
    "idempotency_key": "'${KEY1}'",
    "payload": {"name": "test task"}
}' "${BASE_URL}/api/tasks")
echo "${TASK1}"
TASK1_ID=$(echo "${TASK1}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "Task ID: ${TASK1_ID}"
echo ""

# Test 3: Idempotency - same key should return same task
echo "3. Idempotency test (same key):"
TASK2=$(curl -s -X POST -H "Content-Type: application/json" -d '{
    "type": "example_long_task",
    "idempotency_key": "'${KEY1}'",
    "payload": {"name": "test task"}
}' "${BASE_URL}/api/tasks")
TASK2_ID=$(echo "${TASK2}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "Same task ID: $([[ "${TASK1_ID}" == "${TASK2_ID}" ]] && echo "true" || echo "false")"
echo ""

# Test 4: Different idempotency key - new task
echo "4. New task with different key:"
TASK3=$(curl -s -X POST -H "Content-Type: application/json" -d '{
    "type": "example_long_task",
    "idempotency_key": "'${KEY2}'",
    "payload": {"name": "another test"}
}' "${BASE_URL}/api/tasks")
TASK3_ID=$(echo "${TASK3}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "New task ID: ${TASK3_ID}"
echo ""

# Test 5: Get task details
echo "5. Get task details:"
curl -s "${BASE_URL}/api/tasks/${TASK1_ID}"
echo ""
echo ""

# Test 6: List tasks
echo "6. List tasks:"
curl -s "${BASE_URL}/api/tasks" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f"Total: {d[\"total\"]}")'
echo ""

# Test 7: Cancel task 3
echo "7. Cancel task:"
curl -s -X POST "${BASE_URL}/api/tasks/${TASK3_ID}/cancel"
echo ""
echo ""

# Test 8: Filter by RUNNING status
echo "8. Filter by RUNNING status:"
curl -s "${BASE_URL}/api/tasks?status=RUNNING" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f"Running: {len(d[\"items\"])}")'
echo ""

# Test 9: Filter by CANCELLED status
echo "9. Filter by CANCELLED status:"
curl -s "${BASE_URL}/api/tasks?status=CANCELLED" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f"Cancelled: {len(d[\"items\"])}")'
echo ""

# Test 10: Check progress updates
echo "10. Checking progress updates:"
for i in 1 2 3; do
    sleep 1
    curl -s "${BASE_URL}/api/tasks/${TASK1_ID}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f"  Progress: {d[\"progress\"]}%, Stage: {d[\"stage\"]}")'
done
echo ""

echo "=== All tests completed ==="
