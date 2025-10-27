"""Tests for configuration loading and fallbacks."""

from __future__ import annotations

import textwrap

import paptool.config as config


def test_minimal_yaml_loader_handles_nested_dicts_and_lists(tmp_path, monkeypatch):
    sample = textwrap.dedent(
        """
        # sample config
        connectors:
          rss:
            feeds:
              - "https://example.com/feed"
          email:
            enabled: false
        vocabulary:
          keywords:
            "unit base": 3.5
          negative_keywords:
            - "wedding"
        """
    ).strip()

    cfg_path = tmp_path / "pap_config.yaml"
    cfg_path.write_text(sample, encoding="utf-8")

    monkeypatch.setattr(config, "yaml", None)
    loaded = config._load_config_text(cfg_path.read_text(encoding="utf-8"))

    assert loaded["connectors"]["rss"]["feeds"] == ["https://example.com/feed"]
    assert loaded["connectors"]["email"]["enabled"] is False
    assert loaded["vocabulary"]["keywords"]["unit base"] == 3.5
    assert loaded["vocabulary"]["negative_keywords"] == ["wedding"]


def test_ensure_config_uses_minimal_loader_when_pyyaml_missing(tmp_path, monkeypatch):
    cfg_path = tmp_path / "pap_config.yaml"
    cfg_path.write_text("connectors:\n  rss:\n    feeds:\n      - \"https://a.example/rss\"\n", encoding="utf-8")

    monkeypatch.setattr(config, "yaml", None)

    cfg = config.ensure_config(str(cfg_path))

    assert cfg.connectors["rss"]["feeds"] == ["https://a.example/rss"]
