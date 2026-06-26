from __future__ import annotations

import pytest

from post_analyzer.config import LLMManagerSettings, LLMProviderSettings
from post_analyzer.llm_errors import LLMConfigError, LLMSwitchError
from post_analyzer.llm_factory import LLMFactory
from post_analyzer.llm_manager import LLMProviderManager


class DummyClient:
    def __init__(self, *, value: str = "ok", fail: bool = False) -> None:
        self.value = value
        self.fail = fail
        self.test_called = 0
        self.complete_called = 0

    def test_connection(self) -> None:
        self.test_called += 1
        if self.fail:
            raise RuntimeError("healthcheck failed")

    def complete(self, *, system: str | None, user: str) -> str:
        self.complete_called += 1
        if self.fail:
            raise RuntimeError("complete failed")
        return self.value


class DummyFactory(LLMFactory):
    def __init__(self) -> None:
        self.created: list[LLMProviderSettings] = []

    def create_client(self, settings: LLMProviderSettings):
        self.created.append(settings)
        if settings.model == "bad-factory":
            raise RuntimeError("factory failed")
        if settings.provider == "openai":
            return DummyClient()
        if settings.provider == "ollama":
            return DummyClient(value="ollama-ok")
        return DummyClient(value="fake-ok")


def test_manager_init_fake_success():
    settings = LLMManagerSettings(primary=LLMProviderSettings(provider="fake", mode="fake"))
    mgr = LLMProviderManager(settings=settings, factory=DummyFactory())
    desc = mgr.describe()
    assert desc["provider"] == "fake"
    assert desc["mode"] == "fake"


def test_validation_error_openai_missing_key():
    settings = LLMManagerSettings(
        primary=LLMProviderSettings(
            provider="openai",
            mode="real",
            model="gpt-test",
            api_key=None,
            base_url="https://api.openai.com/v1",
        )
    )
    with pytest.raises(LLMConfigError):
        _ = LLMProviderManager(settings=settings, factory=DummyFactory())


def test_openai_allows_missing_key_for_local_base_url():
    settings = LLMManagerSettings(
        primary=LLMProviderSettings(
            provider="openai",
            mode="real",
            model="deepseek-coder-v2-lite-instruct",
            api_key=None,
            base_url="http://127.0.0.1:1234/v1",
        )
    )
    _ = LLMProviderManager(settings=settings, factory=DummyFactory())


def test_switch_success_with_healthcheck():
    class TrackingFactory(DummyFactory):
        def __init__(self) -> None:
            super().__init__()
            self.last_client: DummyClient | None = None

        def create_client(self, settings: LLMProviderSettings):
            client = super().create_client(settings)
            assert isinstance(client, DummyClient)
            self.last_client = client
            return client

    factory = TrackingFactory()
    mgr = LLMProviderManager(
        settings=LLMManagerSettings(primary=LLMProviderSettings(provider="fake", mode="fake")),
        factory=factory,
    )

    mgr.switch(
        primary=LLMProviderSettings(provider="openai", mode="real", model="gpt-test", api_key="x"),
        fallback=None,
    )

    desc = mgr.describe()
    assert desc["provider"] == "openai"
    assert desc["mode"] == "real"
    assert factory.last_client is not None
    # Health-check should have been invoked during switch in real mode.
    assert factory.last_client.test_called == 1


def test_switch_rollback_on_validation_error():
    factory = DummyFactory()
    mgr = LLMProviderManager(
        settings=LLMManagerSettings(primary=LLMProviderSettings(provider="openai", mode="real", model="gpt", api_key="x")),
        factory=factory,
    )
    before = mgr.describe()

    with pytest.raises(LLMSwitchError):
        mgr.switch(primary=LLMProviderSettings(provider="openai", mode="real", model=None, api_key="x"))

    after = mgr.describe()
    assert after == before


def test_switch_rollback_on_factory_error():
    factory = DummyFactory()
    mgr = LLMProviderManager(
        settings=LLMManagerSettings(primary=LLMProviderSettings(provider="openai", mode="real", model="gpt", api_key="x")),
        factory=factory,
    )
    before = mgr.describe()

    with pytest.raises(LLMSwitchError):
        mgr.switch(primary=LLMProviderSettings(provider="openai", mode="real", model="bad-factory", api_key="x"))

    after = mgr.describe()
    assert after == before


def test_fake_mode_skips_healthcheck_and_allows_missing_key():
    factory = DummyFactory()
    mgr = LLMProviderManager(
        settings=LLMManagerSettings(primary=LLMProviderSettings(provider="fake", mode="fake")),
        factory=factory,
    )

    # OpenAI but fake mode: should not require api_key/model and should not health-check.
    mgr.switch(primary=LLMProviderSettings(provider="openai", mode="fake", model=None, api_key=None))
    desc = mgr.describe()
    assert desc["provider"] == "openai"
    assert desc["mode"] == "fake"

