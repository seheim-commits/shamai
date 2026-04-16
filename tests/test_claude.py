import os
import pytest
from unittest.mock import patch, MagicMock

os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"

from api.claude import analyze_stream, SYSTEM_PROMPT


def test_system_prompt_is_hebrew():
    assert "עברית" in SYSTEM_PROMPT or "שמאי" in SYSTEM_PROMPT


def test_analyze_stream_yields_chunks():
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["chunk1", " chunk2", " chunk3"])

    with patch("api.claude.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream_ctx
        chunks = list(analyze_stream("some text", "סכם"))

    assert chunks == ["chunk1", " chunk2", " chunk3"]


def test_analyze_stream_passes_text_in_message():
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter([])

    with patch("api.claude.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream_ctx
        list(analyze_stream("decision text here", "מה השווי?"))

    call_kwargs = mock_client.messages.stream.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "decision text here" in user_content
    assert "מה השווי?" in user_content
    assert call_kwargs["model"] == "claude-opus-4-6"
