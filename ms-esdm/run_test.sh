#!/bin/bash
echo "--- Running Concurrency Test ---"
#python3 test_concurrency.py
echo ""
echo "--- Running General Magma API Test ---"
python3 test_magma_api.py
echo ""
echo "--- Running Volcanic API Test ---"
python3 test_volcanic_api.py
echo ""
echo "--- Running Simplified API Test ---"
python3 test_simplified_api.py
echo ""
echo "--- All tests complete. ---"
