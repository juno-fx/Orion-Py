#!/bin/bash

pytest tests/test_orionrequests.py -x -s -vvv --durations=5 --color=yes -W ignore::DeprecationWarning
exit_code=$?

echo "Unit test exit code: $exit_code"

exit "$exit_code"
