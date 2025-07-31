#!/usr/bin/env python3
"""
Script to convert logged JSON traces into an XES event log using PM4Py.

Usage:
    python xes.py --name NAME

Reads all .json files from logs/NAME/, interprets each file as a Trace,
transforms event attributes, stores cluster at case level,
and writes the resulting EventLog to NAME.xes using a line-by-line exporter.
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from pm4py.objects.log.obj import EventLog, Trace, Event
from pm4py.objects.log.exporter.xes.variants import line_by_line


def load_json_traces(logs_path: Path):
    """Yield (trace_id, events_list, cluster) for each JSON file in logs_path."""
    for json_file in sorted(logs_path.glob('*.json')):
        trace_id = json_file.stem
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: could not load {json_file}: {e}")
            continue

        # Extract cluster attribute if present
        cluster = None
        if isinstance(data, dict) and 'cluster' in data:
            cluster = data.get('cluster')

        # Determine events list
        if isinstance(data, dict) and 'events' in data and isinstance(data['events'], list):
            events = data['events']
        elif isinstance(data, list):
            events = data
        else:
            print(f"Warning: {json_file} has no events list; skipping.")
            continue

        yield trace_id, events, cluster


def build_event_log(traces):
    """Construct an EventLog from iterable of (trace_id, events_list, cluster)."""
    log = EventLog()

    for trace_id, events, cluster in traces:
        trace = Trace()
        # Set trace-level attributes
        trace.attributes['concept:name'] = trace_id
        if cluster is not None:
            trace.attributes['cluster'] = cluster

        for ev in events:
            # Rename event keys: activity -> concept:name, timestamp -> time:timestamp
            if 'activity' in ev:
                ev['concept:name'] = ev.pop('activity')
            if 'timestamp' in ev:
                ev['time:timestamp'] = ev.pop('timestamp')

            # Convert time:timestamp string and replace '+00:00' suffix with 'Z'
            if 'time:timestamp' in ev and isinstance(ev['time:timestamp'], str):
                ts_str = ev['time:timestamp']
                # Replace '+00:00' with 'Z' for UTC representation
                if ts_str.endswith('+00:00'):
                    ts_str = ts_str[:-6] + 'Z'
                # Normalize for parsing: convert 'Z' back to '+00:00'
                parse_str = ts_str.replace('Z', '+00:00') if ts_str.endswith('Z') else ts_str
                try:
                    ev['time:timestamp'] = datetime.fromisoformat(parse_str)
                except ValueError:
                    # Fall back to original string if parsing fails
                    print(f"Warning: failed to parse timestamp '{ev['time:timestamp']}' for event in trace {trace_id}")

            # Create Event object with updated attributes
            evt = Event(ev)
            trace.append(evt)

        log.append(trace)

    return log


def main():
    parser = argparse.ArgumentParser(description="Export logged JSON traces to XES using PM4Py")
    parser.add_argument('--name', required=True, help='Process name identifier')
    args = parser.parse_args()

    logs_dir = Path('logs') / args.name
    if not logs_dir.is_dir():
        print(f"Error: logs directory not found: {logs_dir}")
        sys.exit(1)

    # Load and build log
    traces = load_json_traces(logs_dir)
    event_log = build_event_log(traces)

    # Export to XES using line-by-line exporter
    xes_file = f"{args.name}.xes"
    try:
        line_by_line.apply(event_log, "logs/" + xes_file)
        print(f"Successfully exported XES to {xes_file}")
    except Exception as e:
        print(f"Error writing XES file: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()