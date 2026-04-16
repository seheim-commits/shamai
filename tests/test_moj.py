import pytest
import httpx
from unittest.mock import patch, MagicMock

from api.moj import search_decisions, get_committees, get_appraisers, get_versions, pdf_url, HEADERS


def test_pdf_url_builds_correctly():
    token = "abc123"
    url = pdf_url(token)
    assert url.endswith("/abc123")
    assert "free-justice.openapi.gov.il" in url


def test_search_decisions_sends_correct_body():
    mock_response = MagicMock()
    mock_response.json.return_value = {"TotalResults": 0, "Results": []}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = search_decisions(skip=10, Committee="תל אביב-יפו", Block="6106")

    call_kwargs = mock_client.post.call_args
    body = call_kwargs[1]["json"]
    assert body["skip"] == 10
    assert body["Committee"] == "תל אביב-יפו"
    assert body["Block"] == "6106"
    assert "DecisiveAppraiser" not in body  # empty filters are excluded
    assert result == {"TotalResults": 0, "Results": []}


def test_search_decisions_uses_required_headers():
    mock_response = MagicMock()
    mock_response.json.return_value = {"TotalResults": 0, "Results": []}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        search_decisions(skip=0)

    headers = mock_client.post.call_args[1]["headers"]
    assert headers["x-client-id"] == "149a5bad-edde-49a6-9fb9-188bd17d4788"
    assert "gov.il" in headers["origin"]


def test_get_committees_returns_list():
    mock_response = MagicMock()
    mock_response.json.return_value = ["תל אביב-יפו", "ירושלים"]
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = get_committees()

    assert result == ["תל אביב-יפו", "ירושלים"]
