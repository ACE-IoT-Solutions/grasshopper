#!/bin/bash
# Script to run tests for Grasshopper

set -e  # Exit immediately if a command exits with a non-zero status

# Default values
COVERAGE=false
VERBOSE=false
API_ONLY=false
DEBUG=false

# Parse command-line options
while [[ $# -gt 0 ]]; do
  case $1 in
    --coverage)
      COVERAGE=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --api-only)
      API_ONLY=true
      shift
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--coverage] [--verbose|-v] [--api-only] [--debug]"
      exit 1
      ;;
  esac
done

# Build command options
OPTIONS=""
if $VERBOSE; then
  OPTIONS="$OPTIONS -v"
fi

if $COVERAGE; then
  OPTIONS="$OPTIONS --cov=Grasshopper/grasshopper --cov-report=term"
fi

if $DEBUG; then
  OPTIONS="$OPTIONS -m debug"
fi

# Determine test paths
if $API_ONLY; then
  TEST_PATH="tests/api/"
else
  TEST_PATH="tests/"
fi

# Print configuration
echo "Running tests with the following configuration:"
echo "- Coverage: $COVERAGE"
echo "- Verbose: $VERBOSE"
echo "- API Only: $API_ONLY"
echo "- Debug: $DEBUG"
echo "- Test Path: $TEST_PATH"
echo "- Options: $OPTIONS"
echo ""

# Run the tests
if $API_ONLY && $DEBUG; then
  # If debug flag is used with API-only, run the debug test module
  echo "Running debug tests..."
  python -m pytest tests/api/test_debug_uploads.py $OPTIONS
else
  # Run normal tests
  echo "Running tests..."
  python -m pytest $TEST_PATH $OPTIONS
fi

# If coverage is enabled, print a reminder about the report
if $COVERAGE; then
  echo ""
  echo "Coverage report generated above."
  echo "For a detailed HTML report, run:"
  echo "pytest $TEST_PATH --cov=Grasshopper/grasshopper --cov-report=html"
  echo "Then open htmlcov/index.html in your browser."
fi