import os
from typing import Generator
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = (
    "אתה עוזר מומחה בניתוח הכרעות שמאי מכריע ישראלי. "
    "תענה בעברית אלא אם המשתמש מבקש אחרת. "
    "היה תמציתי, מדויק ומקצועי."
)


def analyze_stream(text: str, prompt: str) -> Generator[str, None, None]:
    messages = [
        {
            "role": "user",
            "content": f"להלן טקסט ההכרעה:\n\n{text}\n\n{prompt}",
        }
    ]
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for chunk in stream.text_stream:
            yield chunk
