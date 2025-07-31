#!/usr/bin/env python3
"""
Script to generate multiple OpenAI completions concurrently with validation,
running until the total number of valid outputs in the logs folder reaches
the specified target.

Usage:
    python generate.py --name NAME [--total 2500]

Reads prompt from processes/NAME.txt and schema from schemas/NAME.json
Generates completions using gpt-4.1-mini via OpenAI API
Validates each against the JSON schema and logs valid outputs to logs/NAME/
"""
import os
import sys
import json
import uuid
import argparse
import threading
import requests
from jsonschema import validate, ValidationError
from pathlib import Path

# Constants
API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4.1-mini"
MAX_THREADS = 30


def load_process_files(name: str):
    """Load prompt and JSON schema for the given process name."""
    txt_path = Path("processes") / f"{name}.txt"
    json_path = Path("schemas") / f"{name}.json"

    if not txt_path.is_file():
        print(f"Error: Prompt file not found: {txt_path}")
        sys.exit(1)
    if not json_path.is_file():
        print(f"Error: Schema file not found: {json_path}")
        sys.exit(1)

    prompt = txt_path.read_text(encoding="utf-8")
    schema = json.loads(json_path.read_text(encoding="utf-8"))
    return prompt, schema


def init_logging(name: str):
    """Ensure logs directory exists for the process."""
    log_dir = Path("logs") / name
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def call_openai(prompt: str, api_key: str):
    """Make a request to OpenAI and return the JSON response."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "n": 1,
    }
    resp = requests.post(API_URL, headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


def worker(prompt: str,
           schema: dict,
           api_key: str,
           log_dir: Path,
           target_total: int,
           counter: dict,
           counter_lock: threading.Lock):
    """
    Thread worker: keep calling the API until we've written target_total valid JSONs.
    Uses counter['value'] under counter_lock to coordinate across threads.
    """
    while True:
        # Check if we're done
        with counter_lock:
            if counter['value'] >= target_total:
                return

        # Call the API
        try:
            result = call_openai(prompt, api_key)
            content = result['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"[Thread {threading.get_ident()}] Request error: {e}")
            continue

        # Validate JSON
        try:
            data = json.loads(content)
            validate(instance=data, schema=schema)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"[Thread {threading.get_ident()}] Validation error: {e}")
            continue

        # Write out if there's still room
        with counter_lock:
            if counter['value'] < target_total:
                file_id = uuid.uuid4()
                out_path = log_dir / f"{file_id}.json"
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                counter['value'] += 1
                if counter['value'] % 100 == 0 or counter['value'] == target_total:
                    print(f"Written {counter['value']} valid outputs so far.")
            else:
                # Another thread just hit the target
                return


def main():
    parser = argparse.ArgumentParser(description="Concurrent OpenAI process runner")
    parser.add_argument('--name', required=True, help='Process name identifier')
    parser.add_argument(
        '--total',
        type=int,
        default=2500,
        help='Total number of valid JSON outputs to generate'
    )
    args = parser.parse_args()

    # Load prompt and schema
    prompt, schema = load_process_files(args.name)

    # Read API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    # Init logging dir and count existing outputs
    log_dir = init_logging(args.name)
    existing = len(list(log_dir.glob("*.json")))
    print(f"Found {existing} existing outputs in {log_dir}")

    if existing >= args.total:
        print(f"Already have {existing} ≥ target {args.total}; nothing to do.")
        return

    # Shared counter and lock
    counter = {'value': existing}
    counter_lock = threading.Lock()

    # Launch worker threads
    num_threads = min(MAX_THREADS, args.total - existing)
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(
            target=worker,
            args=(prompt, schema, api_key, log_dir, args.total, counter, counter_lock),
            daemon=True
        )
        t.start()
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()

    print(f"Completed: {counter['value']} valid outputs written to {log_dir}")


if __name__ == '__main__':
    main()
