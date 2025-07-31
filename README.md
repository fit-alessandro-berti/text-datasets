# Text Datasets - Simulated Process Mining Event Logs

This project generates synthetic event logs for process mining research and analysis. It uses OpenAI's GPT-4.1-mini model to create realistic process traces that can be used for testing process mining algorithms and techniques.

## Overview

The system generates event logs for multiple business processes by:
1. Using LLM prompts to generate individual process traces as JSON
2. Validating each trace against a predefined JSON schema
3. Converting the validated traces into XES (eXtensible Event Stream) format for process mining tools

## Simulated Processes

The project includes four different business process simulations:

### 1. Customer Support
- **Description**: Customer service interactions including issue reporting, agent responses, and resolution
- **Clusters**: Refund, Delivery Delay, Product Defect, Other
- **Activities**: 15 general-purpose activities from "Issue Reported" to "Case Archived"
- **Features**: Sentiment analysis for each activity (Positive/Neutral/Negative)

### 2. Insurance Claims
- **Description**: Insurance claim processing workflow
- **Activities**: Claim submission, verification, assessment, and settlement processes

### 3. Loan Application
- **Description**: Loan application processing from submission to approval/rejection
- **Activities**: Application submission, document verification, credit checks, and decision making

### 4. Recruitment
- **Description**: Hiring process from job posting to candidate onboarding
- **Activities**: Application screening, interviews, assessments, and hiring decisions

## Project Structure

```
text-datasets/
├── processes/          # Process prompt definitions
│   ├── customer_support.txt
│   ├── insurance_claims.txt
│   ├── loan_application.txt
│   └── recruitment.txt
├── schemas/           # JSON schemas for validation
│   ├── customer_support.json
│   ├── insurance_claims.json
│   ├── loan_application.json
│   └── recruitment.json
├── logs/              # Generated event logs
│   ├── customer_support/
│   │   └── *.json    # Individual trace files
│   ├── insurance_claims/
│   ├── loan_application/
│   ├── recruitment/
│   └── *.xes         # Converted XES files
├── generate.py        # Main generation script
├── xes.py            # XES conversion utility
└── README.md         # This file
```

## Scripts

### generate.py
Generates synthetic process traces using OpenAI's API:
- Reads process prompts from `processes/` directory
- Validates outputs against JSON schemas in `schemas/`
- Saves valid traces to `logs/<process_name>/`
- Supports concurrent generation with up to 30 threads
- Default target: 2,500 traces per process

**Usage:**
```bash
python generate.py --name <process_name> [--total <number>]
```

### xes.py
Converts JSON traces to XES format for process mining tools:
- Reads all JSON files from `logs/<process_name>/`
- Transforms event attributes (activity → concept:name, timestamp → time:timestamp)
- Preserves cluster information at the case level
- Outputs to `logs/<process_name>.xes`

**Usage:**
```bash
python xes.py --name <process_name>
```

## Requirements

- Python 3.x
- PM4Py library for XES handling
- OpenAI API key (set as environment variable `OPENAI_API_KEY`)
- jsonschema library for validation

## Workflow

1. **Define Process**: Create a prompt file in `processes/` describing the process and its activities
2. **Create Schema**: Define a JSON schema in `schemas/` for validation
3. **Generate Traces**: Run `generate.py` to create synthetic traces
4. **Convert to XES**: Use `xes.py` to convert JSON traces to XES format
5. **Analyze**: Import the XES file into process mining tools (ProM, Disco, etc.)

## Data Format

Each generated trace contains:
- **Trace ID**: Unique identifier (UUID)
- **Cluster** (optional): Process variant or category
- **Events**: Sequence of activities with:
  - Activity name
  - Timestamp (ISO format)
  - Contextual information (e.g., sentiment)
  - Message/description

## Notes

- The generation process uses OpenAI's API and may incur costs
- Generated data is synthetic and should not be used as real business data
- XES files can be opened with standard process mining tools
- The system handles timestamp formatting and ensures chronological ordering