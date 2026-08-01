"""Local subprocess entry point: one JSON event on stdin, one envelope out.

Run as ``python -m backend.fallback_lambda.local_run`` by the API client
when EXERCISE_LAMBDA_FUNCTION is unset (dev, CI, emergency prod fallback).
A fresh interpreter with a scrubbed environment — not a fork of the API
process — so student code never inherits secrets, DB sockets, or the API
heap. Inside, the same fork/soft-timer/hard-kill machinery as the Lambda
runs (handler → run_*_isolated).

The result is written to a dup of the original stdout taken before fd 1 is
pointed at /dev/null, so student code that writes to fd 1 directly (bypassing
sys.stdout redirection) cannot corrupt the JSON the API client parses.
"""

import json
import os
import sys

from backend.fallback_lambda.handler import handle


def main() -> None:
    event = json.loads(sys.stdin.read())
    result_fd = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.close(devnull)
    envelope = handle(event)
    os.write(result_fd, json.dumps(envelope).encode())
    os.close(result_fd)


if __name__ == "__main__":
    main()
