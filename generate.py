#!/usr/bin/env python3
"""
Script to generate multiple OpenAI completions concurrently with validation.
Usage:
    python process_runner.py --name NAME

Reads prompt from processes/NAME.txt and schema from schemas/NAME.json
Generates 20 completions using gpt-4.1-mini via OpenAI API
Validates each against the JSON schema and logs valid outputs to logs/NAME/
"""
import os
import sys
import json
import uuid
import argparse
import threading
import queue
import requests
from jsonschema import validate, ValidationError
from pathlib import Path

# Constants
API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4.1-mini"
MAX_THREADS = 30
TOTAL_REQUESTS = 2500


def load_process_files(name: str):
    """Load prompt and JSON schema for the given process name."""
    # Prompt in processes/, schema in schemas/
    txt_base = Path("processes")
    schema_base = Path("schemas")
    txt_path = txt_base / f"{name}.txt"
    json_path = schema_base / f"{name}.json"

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
    """Make a request to OpenAI and return the JSON response or raise."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "n": 1,
    }
    response = requests.post(API_URL, headers=headers, json=body)
    response.raise_for_status()
    return response.json()


def worker(task_queue: queue.Queue, prompt: str, schema: dict, api_key: str, log_dir: Path):
    """Thread worker: get index from queue, call API, validate and log."""
    while True:
        try:
            idx = task_queue.get_nowait()
        except queue.Empty:
            return

        try:
            result = call_openai(prompt, api_key)
            content = result.get('choices', [])[0].get('message', {}).get('content', '').strip()
        except Exception as e:
            print(f"[Thread {threading.get_ident()}] Request error: {e}")
            task_queue.task_done()
            continue

        # Validate against schema
        try:
            data = json.loads(content)
            validate(instance=data, schema=schema)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"[Thread {threading.get_ident()}] Validation error: {e}")
        else:
            file_id = uuid.uuid4()
            out_path = log_dir / f"{file_id}.json"
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        finally:
            task_queue.task_done()


def main():
    parser = argparse.ArgumentParser(description="Concurrent OpenAI process runner")
    parser.add_argument('--name', required=True, help='Process name identifier')
    args = parser.parse_args()

    # Load prompt and schema
    prompt, schema = load_process_files(args.name)

    # Read API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    # Init logging dir
    log_dir = init_logging(args.name)

    # Prepare tasks
    task_queue = queue.Queue()
    for _ in range(TOTAL_REQUESTS):
        task_queue.put(None)

    # Launch threads
    threads = []
    for _ in range(min(MAX_THREADS, TOTAL_REQUESTS)):
        t = threading.Thread(target=worker, args=(task_queue, prompt, schema, api_key, log_dir), daemon=True)
        t.start()
        threads.append(t)

    # Wait for all tasks to complete
    task_queue.join()
    print("All tasks completed.")


if __name__ == '__main__':
    main()