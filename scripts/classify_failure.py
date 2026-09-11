#!/usr/bin/env python3
"""Classifies a CI failure log using Groq's LLM API.

Reads a build log, asks the model to categorize the root cause, and writes
classification.json. Also appends category/auto_fixable to $GITHUB_OUTPUT so
downstream workflow jobs can branch on them.

Usage: classify_failure.py <path-to-build.log>
Requires: GROQ_API_KEY env var.
"""
import json
import os
import re
import sys
import urllib.request

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
MAX_LOG_CHARS = 8000

SYSTEM_PROMPT = """You are a CI/CD failure triage assistant. You will be given \
the tail of a Maven build log from a failed GitHub Actions run. Classify the \
root cause into exactly one category:

- "deterministic_bug": a test failed because of a real logic error in \
application code (e.g. an assertion mismatch on a fixed input/output pair). \
Reliable to reproduce, safe to auto-fix by reverting/correcting the offending \
code if the correct behavior is obvious from the test expectation.
- "flaky_test": the failure is timing-, concurrency-, or environment-dependent \
(e.g. a latency budget, a race condition, a nondeterministic assertion) rather \
than a real logic error. NOT safe to "fix" by editing code — the right action \
is to flag/quarantine and rerun.
- "dependency_issue": the build failed to resolve or use a dependency (e.g. \
missing artifact, bad version, incompatible version). Safe to auto-fix only if \
reverting to a previously-known-good dependency version is obviously correct.
- "unknown": none of the above clearly applies, or there isn't enough signal.

Respond with ONLY a JSON object, no prose, matching this exact shape:
{
  "category": "deterministic_bug" | "flaky_test" | "dependency_issue" | "unknown",
  "confidence": <float 0-1>,
  "root_cause": "<one or two sentence explanation of what went wrong>",
  "auto_fixable": <true if and only if category is deterministic_bug or \
dependency_issue AND you are confident the fix is a simple revert, false otherwise>,
  "suggested_fix_summary": "<one sentence describing the fix, or empty string \
if auto_fixable is false>"
}
"""


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"Could not parse JSON from model response: {text!r}")


def classify(log_text: str, api_key: str) -> dict:
    payload = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Build log tail:\n\n{log_text}"},
        ],
    }
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    return extract_json(content)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: classify_failure.py <path-to-build.log>", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    log_path = sys.argv[1]
    with open(log_path, "r", errors="replace") as f:
        log_text = f.read()[-MAX_LOG_CHARS:]

    result = classify(log_text, api_key)
    result.setdefault("category", "unknown")
    result.setdefault("confidence", 0.0)
    result.setdefault("root_cause", "")
    result.setdefault("auto_fixable", False)
    result.setdefault("suggested_fix_summary", "")

    with open("classification.json", "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"category={result['category']}\n")
            f.write(f"auto_fixable={'true' if result['auto_fixable'] else 'false'}\n")


if __name__ == "__main__":
    main()
