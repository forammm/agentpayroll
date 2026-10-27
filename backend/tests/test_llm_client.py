"""Tests app.langgraph_app.tools.llm_client.AnthropicExplanationClient's own
request/response handling, with the underlying anthropic SDK client mocked out -
no network call and no API key required. See test_verification_graph.py for
tests of the explanation NODE's fallback behavior, and test_verification_api.py
for an end-to-end run against the real (unconfigured) client."""

from unittest.mock import MagicMock

import anthropic
import pytest

from app.langgraph_app.tools.llm_client import AnthropicExplanationClient, LlmGenerationError
from app.schemas.verification import VerificationExplanation


def _client_with_mocked_sdk(parse_return=None, parse_side_effect=None):
    mock_sdk_client = MagicMock()
    mock_with_options = MagicMock()
    mock_sdk_client.with_options.return_value = mock_with_options
    if parse_side_effect is not None:
        mock_with_options.messages.parse.side_effect = parse_side_effect
    else:
        mock_with_options.messages.parse.return_value = parse_return
    return AnthropicExplanationClient(client=mock_sdk_client), mock_sdk_client


def test_successful_call_returns_the_parsed_explanation():
    expected = VerificationExplanation(summary="ok", evidence=["e"], uncertainties=[], next_steps=["n"])
    fake_response = MagicMock(stop_reason="end_turn", parsed_output=expected)
    client, _ = _client_with_mocked_sdk(parse_return=fake_response)

    result = client.generate_explanation({"classification": "MATCH"})

    assert result == expected


def test_refusal_stop_reason_raises_llm_generation_error():
    fake_response = MagicMock(stop_reason="refusal", parsed_output=None)
    client, _ = _client_with_mocked_sdk(parse_return=fake_response)

    with pytest.raises(LlmGenerationError, match="declined"):
        client.generate_explanation({"classification": "MATCH"})


def test_missing_parsed_output_raises_llm_generation_error():
    fake_response = MagicMock(stop_reason="end_turn", parsed_output=None)
    client, _ = _client_with_mocked_sdk(parse_return=fake_response)

    with pytest.raises(LlmGenerationError, match="schema"):
        client.generate_explanation({"classification": "MATCH"})


def test_sdk_rate_limit_error_is_converted_to_llm_generation_error():
    error = anthropic.RateLimitError("rate limited", response=MagicMock(headers={}), body=None)
    client, _ = _client_with_mocked_sdk(parse_side_effect=error)

    with pytest.raises(LlmGenerationError):
        client.generate_explanation({"classification": "MATCH"})


def test_unexpected_non_sdk_exception_is_still_converted_to_llm_generation_error():
    # Covers the real missing-credentials case, which raises a plain TypeError
    # from the SDK rather than an anthropic.AnthropicError subclass - verified
    # directly against the real client during development (no mock involved).
    client, _ = _client_with_mocked_sdk(parse_side_effect=TypeError("Could not resolve authentication method"))

    with pytest.raises(LlmGenerationError):
        client.generate_explanation({"classification": "MATCH"})


def test_request_passes_configured_model_and_output_schema():
    expected = VerificationExplanation(summary="ok", evidence=[], uncertainties=[], next_steps=[])
    fake_response = MagicMock(stop_reason="end_turn", parsed_output=expected)
    client, mock_sdk_client = _client_with_mocked_sdk(parse_return=fake_response)

    client.generate_explanation({"classification": "MATCH", "employer_name": "Acme"})

    call_kwargs = mock_sdk_client.with_options.return_value.messages.parse.call_args.kwargs
    assert call_kwargs["output_format"] is VerificationExplanation
    assert "Acme" in call_kwargs["messages"][0]["content"]
    assert call_kwargs["messages"][0]["role"] == "user"
