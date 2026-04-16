#!/bin/bash

coverage run -m pytest -x -s -vvv --durations=5 --color=yes tests/ -W ignore::DeprecationWarning
cov_exit_code=$?

coverage report -m --fail-under=100

test_exit_code=$?
exit_code=$((cov_exit_code + test_exit_code))

echo "Coverage exit code: $cov_exit_code"
echo "Test exit code: $test_exit_code"
echo "Exit code: $exit_code"

exit "$exit_code"
