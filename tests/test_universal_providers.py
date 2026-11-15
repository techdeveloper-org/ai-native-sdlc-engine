"""Unit test suite for universal multi-model LLM providers and path resolution.

Tests conform to Triad testing standards (positive, negative, edge-case)
and verify backward compatibility across Claude and universal SDLC environments.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdlc_engine.llm.llm_call import (
    AnthropicProvider,
    ClaudeCLIProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
    _PROVIDER_REGISTRY,
    _build_provider_chain,
)
from sdlc_engine.shared.config.config_loader import _MAPPING, load_workflow_config
from sdlc_engine.shared.config.sdlc_paths import get_engine_home, get_sdlc_home
from sdlc_engine.shared.utils.path_resolver import PathResolver


class TestUniversalProvidersRegistry:
    """Verify provider registration and tier mapping."""

    def test_all_five_providers_registered(self):
        """All universal providers must be registered in _PROVIDER_REGISTRY."""
        assert "gemini" in _PROVIDER_REGISTRY
        assert "anthropic" in _PROVIDER_REGISTRY
        assert "openai" in _PROVIDER_REGISTRY
        assert "claude_cli" in _PROVIDER_REGISTRY
        assert "ollama" in _PROVIDER_REGISTRY

    def test_gemini_provider_availability(self):
        """GeminiProvider should be available only when API key is present."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"}, clear=False):
            provider = GeminiProvider()
            assert provider.is_available() is True
            assert provider.name == "gemini"

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
            provider = GeminiProvider()
            assert provider.is_available() is False

    def test_openai_provider_availability(self):
        """OpenAIProvider should be available only when API key is present."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-123"}, clear=False):
            provider = OpenAIProvider()
            assert provider.is_available() is True
            assert provider.name == "openai"

        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            provider = OpenAIProvider()
            assert provider.is_available() is False

    def test_ollama_provider_tier_mapping(self):
        """OllamaProvider must have valid mappings for standard tiers."""
        provider = OllamaProvider()
        assert "fast" in provider.MODEL_MAP
        assert "balanced" in provider.MODEL_MAP
        assert "deep" in provider.MODEL_MAP


class TestUniversalPathResolution:
    """Verify dual-resolution path hierarchy for universal SDLC Engine."""

    def test_sdlc_home_takes_precedence_over_claude_home(self, tmp_path):
        """SDLC_HOME env var must override CLAUDE_HOME when both are set."""
        sdlc_dir = tmp_path / "sdlc_root"
        claude_dir = tmp_path / "claude_root"
        sdlc_dir.mkdir()
        claude_dir.mkdir()

        with patch.dict(os.environ, {"SDLC_HOME": str(sdlc_dir), "CLAUDE_HOME": str(claude_dir)}, clear=False):
            resolver = PathResolver()
            assert resolver.get_sdlc_home() == sdlc_dir
            assert resolver.get_engine_home() == sdlc_dir
            assert resolver.get_claude_home() == sdlc_dir

    def test_claude_home_fallback_when_sdlc_home_unset(self, tmp_path):
        """CLAUDE_HOME must be honored as seamless backward-compatible fallback."""
        claude_dir = tmp_path / "claude_root"
        claude_dir.mkdir()

        env_clean = {k: v for k, v in os.environ.items() if k != "SDLC_HOME"}
        env_clean["CLAUDE_HOME"] = str(claude_dir)

        with patch.dict(os.environ, env_clean, clear=True):
            resolver = PathResolver()
            assert resolver.get_sdlc_home() == claude_dir
            assert resolver.get_claude_home() == claude_dir

    def test_sdlc_logs_dir_precedence(self, tmp_path):
        """SDLC_LOGS_DIR must take precedence over CLAUDE_LOGS_DIR."""
        logs_custom = tmp_path / "custom_logs"
        logs_custom.mkdir()

        with patch.dict(os.environ, {"SDLC_LOGS_DIR": str(logs_custom)}, clear=False):
            resolver = PathResolver()
            assert resolver.get_sdlc_logs_dir() == logs_custom


class TestUniversalConfigLoader:
    """Verify config mapping and legacy synchronization."""

    def test_multi_model_mappings_present(self):
        """Config loader mapping must include Gemini, OpenAI, and Ollama."""
        assert "gemini.api_key" in _MAPPING
        assert "openai.api_key" in _MAPPING
        assert "ollama.host" in _MAPPING
        assert _MAPPING["gemini.api_key"] == "GEMINI_API_KEY"
        assert _MAPPING["openai.api_key"] == "OPENAI_API_KEY"

    def test_legacy_sync_behavior(self, tmp_path):
        """When SDLC_HOOK_MODE is injected, CLAUDE_HOOK_MODE must also be synced."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"pipeline": {"hook_mode": "1", "debug": "1"}}', encoding="utf-8")

        env_clean = {k: v for k, v in os.environ.items() if "HOOK_MODE" not in k and "DEBUG" not in k}
        with patch.dict(os.environ, env_clean, clear=True):
            injected = load_workflow_config(cfg_file)
            assert os.environ.get("SDLC_HOOK_MODE") == "1"
            assert os.environ.get("CLAUDE_HOOK_MODE") == "1"
