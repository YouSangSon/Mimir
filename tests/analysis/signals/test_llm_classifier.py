"""AnthropicHeadlineClassifier — missing-dependency error path (INC5).

These tests never reach the network. They only assert that constructing the
real classifier WITHOUT the `anthropic` package fails loud with an actionable
message (DoD: "missing-anthropic default classifier -> clear error"). The lazy
import is forced to fail via a builtins.__import__ shim, so the test passes
whether or not `anthropic` is installed.
"""

import builtins

import pytest

from mimir.analysis.signals.llm_sentiment import AnthropicHeadlineClassifier


def test_missing_anthropic_raises_clear_error(monkeypatch):
    real_import = builtins.__import__

    def _no_anthropic(name, *args, **kwargs):
        if name == "anthropic" or name.startswith("anthropic."):
            raise ModuleNotFoundError("No module named 'anthropic'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_anthropic)

    with pytest.raises(RuntimeError, match=r"pip install -e '\.\[llm\]'"):
        AnthropicHeadlineClassifier(api_key="sk-test")
