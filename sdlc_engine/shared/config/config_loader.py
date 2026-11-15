"""
Workflow Config Loader -- reads ~/.claude/workflow-config.json.

Two modes:
  1. load_workflow_config() -- injects values into os.environ (covers any
     remaining os.environ.get() call sites as a safety net).
  2. get_section(name)     -- returns raw JSON section dict so integration
     classes can read values directly without going through os.environ.

Priority for os.environ injection:
  existing os.environ > workflow-config.json (no-override mode)

Usage:
  from sdlc_engine.shared.config.config_loader import load_workflow_config, get_section
  load_workflow_config()           # once at startup in 3-level-flow.py
  cfg = get_section("jira")        # direct dict access anywhere
"""

import json
import os
from pathlib import Path


def _resolve_default_config_path() -> Path:
    """Resolve the default workflow configuration file across universal and legacy locations.

    Returns:
        Path: Resolved configuration file path.
    """
    env_path = os.environ.get("SDLC_CONFIG_FILE") or os.environ.get("CLAUDE_CONFIG_FILE")
    if env_path:
        return Path(env_path)
    sdlc_cfg = Path.home() / ".sdlc" / "config.json"
    if sdlc_cfg.exists():
        return sdlc_cfg
    repo_cfg = Path.cwd() / "sdlc-config.json"
    if repo_cfg.exists():
        return repo_cfg
    return Path.home() / ".claude" / "workflow-config.json"


_DEFAULT_CONFIG_PATH = _resolve_default_config_path()

# Nested JSON key  ->  env var name  (kept for os.environ injection fallback)
_MAPPING: dict[str, str] = {
    "pipeline.hook_mode": "SDLC_HOOK_MODE",
    "pipeline.debug": "SDLC_DEBUG",
    "pipeline.llm_provider": "LLM_PROVIDER",
    "github.token": "GITHUB_TOKEN",
    "github.default_label": "GITHUB_DEFAULT_LABEL",
    "github.owner": "SDLC_GITHUB_OWNER",
    "jira.enabled": "ENABLE_JIRA",
    "jira.url": "JIRA_URL",
    "jira.user": "JIRA_USER",
    "jira.api_token": "JIRA_API_TOKEN",
    "jira.api_version": "JIRA_API_VERSION",
    "jira.auth_method": "JIRA_AUTH_METHOD",
    "jira.default_project": "JIRA_DEFAULT_PROJECT",
    "jira.default_issue_type": "JIRA_DEFAULT_ISSUE_TYPE",
    "jira.default_branch_prefix": "JIRA_DEFAULT_BRANCH_PREFIX",
    "jenkins.enabled": "ENABLE_JENKINS",
    "jenkins.url": "JENKINS_URL",
    "jenkins.user": "JENKINS_USER",
    "jenkins.api_token": "JENKINS_API_TOKEN",
    "jenkins.verify_ssl": "JENKINS_VERIFY_SSL",
    "figma.enabled": "ENABLE_FIGMA",
    "figma.access_token": "FIGMA_ACCESS_TOKEN",
    "figma.team_id": "FIGMA_TEAM_ID",
    "sonarqube.enabled": "ENABLE_SONARQUBE",
    "anthropic.api_key": "ANTHROPIC_API_KEY",
    "anthropic.model_fast": "ANTHROPIC_MODEL_FAST",
    "anthropic.model_balanced": "ANTHROPIC_MODEL_BALANCED",
    "anthropic.model_deep": "ANTHROPIC_MODEL_DEEP",
    "gemini.api_key": "GEMINI_API_KEY",
    "gemini.model_fast": "GEMINI_MODEL_FAST",
    "gemini.model_balanced": "GEMINI_MODEL_BALANCED",
    "gemini.model_deep": "GEMINI_MODEL_DEEP",
    "openai.api_key": "OPENAI_API_KEY",
    "openai.model_fast": "OPENAI_MODEL_FAST",
    "openai.model_balanced": "OPENAI_MODEL_BALANCED",
    "openai.model_deep": "OPENAI_MODEL_DEEP",
    "ollama.host": "OLLAMA_HOST",
    "ollama.model_fast": "OLLAMA_MODEL_FAST",
    "ollama.model_balanced": "OLLAMA_MODEL_BALANCED",
    "ollama.model_deep": "OLLAMA_MODEL_DEEP",
}

# Legacy companion keys that are kept in sync for backward compatibility
_LEGACY_SYNCS: dict[str, str] = {
    "SDLC_HOOK_MODE": "CLAUDE_HOOK_MODE",
    "SDLC_DEBUG": "CLAUDE_DEBUG",
    "SDLC_GITHUB_OWNER": "CLAUDE_GITHUB_OWNER",
}

_CONFIG_CACHE: dict | None = None


def _load_raw(path: Path | None = None) -> dict:
    """Return the full parsed JSON config (cached after first read)."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    config_path = path or _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        _CONFIG_CACHE = {}
        return _CONFIG_CACHE
    try:
        _CONFIG_CACHE = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        import sys

        print(f"[config_loader] WARNING: could not read {config_path}: {exc}", file=sys.stderr)
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE


def get_section(name: str) -> dict:
    """Return the JSON config section for a named integration or service.

    Args:
        name: Top-level key in workflow-config.json, e.g. 'jira', 'jenkins'.

    Returns:
        Dict of config values for that section, or {} when not present.
    """
    return _load_raw().get(name, {})


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    """Recursively flatten nested dict to dot-separated keys."""
    out: dict[str, str] = {}
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, full_key))
        else:
            out[full_key] = str(v)
    return out


# Values that mean "you were supposed to fill this in". The shipped
# workflow-config.json carries them, so an untouched config injects them exactly
# as if they were real credentials.
#
# This is deliberately narrow. A false positive here rejects a working secret and
# breaks a setup that was fine, which is worse than the bug it guards against, so
# nothing is matched on length, entropy or character class -- only on shapes no
# real credential has. A real GitHub token starts ghp_/gho_/github_pat_ and a real
# API key is not spelled CHANGEME.
_PLACEHOLDER_PREFIXES = ("your_", "your-", "my_", "replace_", "replaceme", "changeme", "change_me", "todo", "xxx")


def _is_placeholder(value: str) -> bool:
    """Return True when a config value is an unfilled template, not a secret.

    Args:
        value: The raw value read from workflow-config.json.

    Returns:
        bool: True if the value should be treated as absent.
    """
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped:
        return True
    if stripped.startswith("<") and stripped.endswith(">"):
        return True
    return stripped.lower().startswith(_PLACEHOLDER_PREFIXES)


def load_workflow_config(path: Path | None = None) -> dict[str, str]:
    """Load workflow-config.json and inject into os.environ (no-override).

    Covers any remaining os.environ.get() call sites that have not yet
    been migrated to use get_section() directly.

    Unfilled template values are skipped rather than injected. The reason is
    specific and was expensive: the shipped config carries
    ``"github": {"token": "YOUR_GITHUB_TOKEN"}``, this function injected it into
    GITHUB_TOKEN, and that one string then defeated BOTH GitHub backends at once
    -- the MCP client authenticated with it and got 401 Bad credentials, and the
    gh CLI fallback also lost, because gh prefers an environment token over its
    own keyring and reported itself unauthenticated. `gh auth login` therefore
    appeared to do nothing, and Step 2 fell back to "no GitHub backend available"
    on every run. Injecting nothing leaves the keyring reachable, which is the
    working path.

    Returns a dict of env-var-name -> value pairs that were injected.
    """
    raw = _load_raw(path)
    if not raw:
        return {}

    flat = _flatten(raw)
    injected: dict[str, str] = {}
    skipped: list[str] = []

    for json_key, env_key in _MAPPING.items():
        if json_key not in flat or env_key in os.environ:
            continue
        value = flat[json_key]
        if _is_placeholder(value):
            skipped.append(json_key)
            continue
        os.environ[env_key] = value
        injected[env_key] = value

        # Sync legacy companion env var if defined
        legacy_key = _LEGACY_SYNCS.get(env_key)
        if legacy_key and legacy_key not in os.environ:
            os.environ[legacy_key] = value

    # Said out loud, because a value silently ignored is indistinguishable from a
    # value that was never read -- and the reader is someone wondering why their
    # config has no effect.
    if skipped:
        import sys  # noqa: PLC0415

        print(
            "[config_loader] ignored %d unfilled placeholder value(s): %s" % (len(skipped), ", ".join(sorted(skipped))),
            file=sys.stderr,
        )

    return injected
