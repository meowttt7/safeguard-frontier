"""Check that the Anthropic key in .env works and that the planned models are listed.

Cost: one tiny Haiku 5.5 call, a fraction of a cent. Prints nothing from the key itself.
"""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PLANNED = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is missing. Copy .env.example to .env and paste the key.")
        return 1

    client = anthropic.Anthropic()

    try:
        listed = {m.id for m in client.models.list()}
    except anthropic.AuthenticationError:
        print("The API rejected the key (401). Check the value in .env.")
        return 1
    except anthropic.APIConnectionError:
        print("Could not reach the API. Check the network.")
        return 1

    for model_id in PLANNED:
        print(f"{model_id}: {'listed' if model_id in listed else 'NOT listed'}")

    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=256,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": "Reply with the single word: ready"}],
    )
    if response.stop_reason == "refusal":
        print("Haiku refused the smoke prompt, which should not happen; check stop_details.")
        return 1
    text = next((block.text for block in response.content if block.type == "text"), "")
    usage = response.usage
    print(
        f"haiku replied {text.strip()!r}; stop={response.stop_reason}; "
        f"input_tokens={usage.input_tokens} output_tokens={usage.output_tokens}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
