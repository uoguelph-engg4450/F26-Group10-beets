"""Tests for choosing a translation provider and for translation errors."""

from __future__ import annotations

from http import HTTPStatus
from typing import ClassVar

import pytest
import requests

from beets.library import Item
from beets.util.lyrics import Lyrics
from beetsplug import lyrics

GOOD_TEXT = "Some lyrics\nSome more lyrics"
TRANSLATED = {
    "detectedLanguage": {"language": "en", "score": 1.0},
    "translations": [{"text": " | Quelques paroles", "to": "fr"}],
}


class FakeDeepL(lyrics.Translator):
    """A provider shaped like DeepL: it uses 403 for a bad key, 456 for quota.

    It shows what a provider needs to define to get the shared handling.
    """

    SERVICE = "DeepL"
    TRANSLATE_URL = "https://api-free.deepl.com/v2/translate"
    ERROR_BY_STATUS: ClassVar[dict[int, type[lyrics.TranslatorHTTPError]]] = {
        HTTPStatus.FORBIDDEN: lyrics.InvalidAPIKeyError,
        456: lyrics.QuotaExceededError,
    }

    def get_translations(self, texts):
        self.post_json(self.TRANSLATE_URL, json={"text": list(texts)})
        return [f"translated {t}" for t in texts]


@pytest.fixture
def plugin(config):
    return lyrics.LyricsPlugin()


@pytest.fixture
def providers(monkeypatch):
    """Offer a DeepL-like provider next to Azure."""
    monkeypatch.setitem(lyrics.TRANSLATOR_BY_NAME, "deepl", FakeDeepL)


def translator_for(plugin, **translate):
    plugin.config["translate"].set(translate)
    return plugin.translator


class TestProviderSelection:
    def test_default_provider_is_azure(self, plugin):
        assert plugin.config["translate"]["provider"].get() == "azure"

    @pytest.mark.parametrize("provider", [None, "azure", "Azure", " AZURE "])
    def test_azure_is_used_by_default(self, plugin, provider):
        translate = {"api_key": "key", "to_language": "fr"}
        if provider:
            translate["provider"] = provider

        translator = translator_for(plugin, **translate)

        assert type(translator) is lyrics.Translator
        assert translator.api_key == "key"
        assert translator.to_language == "FR"

    @pytest.mark.parametrize("provider", ["deepl", "DeepL"])
    def test_deepl_can_be_chosen(self, plugin, providers, provider):
        translator = translator_for(
            plugin, provider=provider, api_key="key", to_language="de"
        )

        assert isinstance(translator, FakeDeepL)

    def test_languages_are_normalised(self, plugin):
        translator = translator_for(
            plugin,
            api_key="key",
            to_language=" fr ",
            from_languages=["en", "de"],
        )

        assert translator.to_language == "FR"
        assert translator.from_languages == ["EN", "DE"]

    def test_from_languages_may_be_a_string(self, plugin):
        translator = translator_for(
            plugin, api_key="key", to_language="fr", from_languages="en"
        )

        assert translator.from_languages == ["EN"]

    def test_api_key_is_hidden_in_config_dump(self, plugin, config):
        plugin.config["translate"].set({"api_key": "secret-key"})

        dump = config.dump(redact=True)

        assert "secret-key" not in dump
        assert "provider: azure" in dump


class TestConfigValidation:
    @pytest.fixture(autouse=True)
    def _providers(self, providers):
        """Both providers are available in all validation tests."""

    @staticmethod
    def warnings(caplog):
        return [
            r.getMessage() for r in caplog.records if r.levelname == "WARNING"
        ]

    def test_not_configured_is_silent(self, plugin, caplog):
        assert plugin.translator is None
        assert not self.warnings(caplog)

    def test_unknown_provider(self, plugin, caplog):
        translator = translator_for(
            plugin, provider="google", api_key="key", to_language="fr"
        )

        assert translator is None
        (message,) = self.warnings(caplog)
        assert "unknown translate.provider 'google'" in message
        assert "Choose one of: azure, deepl" in message

    @pytest.mark.parametrize("provider", ["azure", "deepl"])
    def test_missing_api_key(self, plugin, caplog, provider):
        translator = translator_for(plugin, provider=provider, to_language="fr")

        assert translator is None
        (message,) = self.warnings(caplog)
        assert "translate.api_key is not set" in message
        assert "translate.to_language" not in message

    @pytest.mark.parametrize("api_key", ["", "   ", None])
    def test_blank_api_key_counts_as_missing(self, plugin, caplog, api_key):
        translator = translator_for(plugin, api_key=api_key, to_language="fr")

        assert translator is None
        assert "translate.api_key is not set" in self.warnings(caplog)[0]

    def test_missing_to_language(self, plugin, caplog):
        translator = translator_for(plugin, provider="deepl", api_key="key")

        assert translator is None
        (message,) = self.warnings(caplog)
        assert "translate.to_language is not set" in message
        assert "translate.api_key" not in message

    def test_choosing_deepl_alone_reports_everything_missing(
        self, plugin, caplog
    ):
        assert translator_for(plugin, provider="deepl") is None

        (message,) = self.warnings(caplog)
        assert "translate.api_key and translate.to_language are not set" in (
            message
        )

    @pytest.mark.parametrize(
        "translate, expected",
        [({"provider": ["azure", "deepl"]}, "translate.provider")],
    )
    def test_wrong_type_is_reported(self, plugin, caplog, translate, expected):
        translate |= {"api_key": "key", "to_language": "fr"}

        assert translator_for(plugin, **translate) is None

        (message,) = self.warnings(caplog)
        assert "Translation is switched off" in message
        assert expected in message

    def test_problem_is_reported_once(self, plugin, caplog):
        plugin.config["translate"].set({"provider": "deepl"})

        assert plugin.translator is None
        assert plugin.translator is None

        assert len(self.warnings(caplog)) == 1

    def test_api_key_is_not_logged(self, plugin, caplog):
        translator_for(plugin, provider="google", api_key="secret-key")

        assert "secret-key" not in caplog.text


@pytest.mark.requires_import("langdetect")
class TestTranslationErrors:
    @pytest.fixture(autouse=True)
    def _providers(self, providers):
        """Both providers are available in all error tests."""

    @pytest.fixture
    def azure(self, plugin):
        return translator_for(plugin, api_key="key", to_language="fr")

    @pytest.fixture
    def deepl(self, plugin):
        return translator_for(
            plugin, provider="deepl", api_key="key", to_language="fr"
        )

    @pytest.fixture
    def post(self, requests_mock):
        def mock(url, **kwargs):
            return requests_mock.post(url, **kwargs)

        return mock

    @staticmethod
    def translate(translator):
        return translator.translate(Lyrics(GOOD_TEXT), Lyrics(""))

    @staticmethod
    def warnings(caplog):
        return [
            r.getMessage() for r in caplog.records if r.levelname == "WARNING"
        ]

    def test_success_is_unchanged(self, azure, post):
        post(azure.TRANSLATE_URL, json=[TRANSLATED])

        result = self.translate(azure)

        assert result.translated
        assert result.translation_language == "FR"
        assert not azure.disabled

    @pytest.mark.parametrize(
        "status, expected",
        [
            (HTTPStatus.UNAUTHORIZED, "API key was rejected"),
            (HTTPStatus.FORBIDDEN, "quota is used up"),
        ],
    )
    def test_azure_fatal_errors(self, azure, post, caplog, status, expected):
        route = post(azure.TRANSLATE_URL, status_code=status)

        result = self.translate(azure)
        # the next song does not send another request
        self.translate(azure)

        assert route.call_count == 1
        assert azure.disabled
        assert not result.translated
        assert result.translation_language is None
        assert result.full_text == GOOD_TEXT
        (message,) = self.warnings(caplog)
        assert expected in message
        assert "stays off until beets is restarted" in message
        assert "saved untranslated" in message

    @pytest.mark.parametrize(
        "status, expected",
        [
            (HTTPStatus.FORBIDDEN, "API key was rejected"),
            (456, "quota is used up"),
        ],
    )
    def test_deepl_status_codes(self, deepl, post, caplog, status, expected):
        post(deepl.TRANSLATE_URL, status_code=status)

        result = self.translate(deepl)

        assert deepl.disabled
        assert not result.translated
        assert expected in self.warnings(caplog)[0]

    @pytest.mark.parametrize(
        "body",
        [
            (
                '{"error":{"code":400036,"message":"The target language is'
                ' not valid."}}'
            ),
            '{"message":"Value for \'target_lang\' not supported."}',
        ],
    )
    @pytest.mark.parametrize("provider", ["azure", "deepl"])
    def test_unsupported_language(self, plugin, post, caplog, provider, body):
        translator = translator_for(
            plugin, provider=provider, api_key="key", to_language="xx"
        )
        post(
            translator.TRANSLATE_URL,
            status_code=HTTPStatus.BAD_REQUEST,
            text=body,
        )

        result = self.translate(translator)

        assert translator.disabled
        assert not result.translated
        (message,) = self.warnings(caplog)
        assert "language is not supported" in message
        assert "translate.to_language" in message

    def test_provider_may_raise_unsupported_language_itself(
        self, deepl, monkeypatch, caplog
    ):
        def fail(_texts):
            raise lyrics.UnsupportedLanguageError

        monkeypatch.setattr(deepl, "get_translations", fail)

        result = self.translate(deepl)

        assert deepl.disabled
        assert not result.translated
        assert "language is not supported" in self.warnings(caplog)[0]

    def test_provider_error_that_is_not_fatal(
        self, azure, post, monkeypatch, caplog
    ):
        class TooBusyError(lyrics.TranslatorHTTPError):
            MESSAGE = "Too many requests."

        monkeypatch.setitem(
            lyrics.Translator.ERROR_BY_STATUS,
            HTTPStatus.TOO_MANY_REQUESTS,
            TooBusyError,
        )
        route = post(
            azure.TRANSLATE_URL, status_code=HTTPStatus.TOO_MANY_REQUESTS
        )

        self.translate(azure)
        self.translate(azure)

        # only this song is left untranslated, the next one is tried again
        assert route.call_count == 2
        assert not azure.disabled
        assert self.warnings(caplog)[0] == (
            "Translator: Too many requests. Lyrics are saved untranslated."
        )

    def test_other_bad_request_is_not_a_language_error(
        self, azure, post, caplog
    ):
        post(
            azure.TRANSLATE_URL,
            status_code=HTTPStatus.BAD_REQUEST,
            text='{"error":{"message":"Request body is empty."}}',
        )

        result = self.translate(azure)

        assert not azure.disabled
        assert not result.translated
        (message,) = self.warnings(caplog)
        assert "Translation request failed" in message
        assert "language" not in message

    @pytest.mark.parametrize(
        "exc",
        [
            requests.exceptions.ConnectionError("no route to host"),
            requests.exceptions.ConnectTimeout("timed out"),
            requests.exceptions.ReadTimeout("read timed out"),
        ],
    )
    def test_network_errors_are_retried_on_the_next_song(
        self, azure, post, caplog, exc
    ):
        route = post(azure.TRANSLATE_URL, exc=exc)

        first = self.translate(azure)
        second = self.translate(azure)

        assert route.call_count == 2
        assert not azure.disabled
        assert not first.translated
        assert not second.translated
        assert len(self.warnings(caplog)) == 2
        assert "Could not reach Azure Translator" in self.warnings(caplog)[0]
        assert "saved untranslated" in self.warnings(caplog)[0]

    def test_exhausted_retries(self, azure, post, caplog):
        post(azure.TRANSLATE_URL, exc=requests.exceptions.RetryError("busy"))

        result = self.translate(azure)

        assert not azure.disabled
        assert not result.translated
        assert "is busy or unavailable" in self.warnings(caplog)[0]

    def test_server_error(self, azure, post, caplog):
        post(azure.TRANSLATE_URL, status_code=HTTPStatus.BAD_GATEWAY)

        result = self.translate(azure)

        assert not azure.disabled
        assert not result.translated
        assert "Translation request failed" in self.warnings(caplog)[0]
        assert "502" in self.warnings(caplog)[0]

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"text": "not json"},
            {"json": {"unexpected": "shape"}},
            {"json": []},
            {"json": [{"translations": []}]},
            {"json": None},
        ],
        ids=["not json", "wrong keys", "empty list", "no result", "null"],
    )
    def test_unexpected_response(self, azure, post, caplog, kwargs):
        post(azure.TRANSLATE_URL, **kwargs)

        result = self.translate(azure)

        assert not azure.disabled
        assert not result.translated
        (message,) = self.warnings(caplog)
        assert "could not be understood" in message

    def test_api_key_is_not_logged(self, plugin, post, caplog):
        translator = translator_for(
            plugin, api_key="s3cr3t-value", to_language="fr"
        )
        post(translator.TRANSLATE_URL, status_code=HTTPStatus.UNAUTHORIZED)
        caplog.set_level("DEBUG")

        self.translate(translator)

        assert "s3cr3t-value" not in caplog.text

    def test_old_translations_are_reused_after_an_error(self, azure, post):
        route = post(azure.TRANSLATE_URL, status_code=HTTPStatus.UNAUTHORIZED)
        self.translate(azure)
        old = Lyrics(
            "Some lyrics / Some translation",
            language="EN",
            translation_language="FR",
        )

        result = azure.translate(Lyrics("Some lyrics"), old)

        assert result is old
        assert route.call_count == 1


@pytest.mark.requires_import("langdetect")
class TestFetchingWithTranslationErrors:
    """A translation problem must not stop lyrics from being stored."""

    @pytest.fixture
    def item(self, module_helper):
        return module_helper.add_item(
            id=1, title="Song", artist="Artist", lyrics=""
        )

    @pytest.mark.parametrize("status", [HTTPStatus.UNAUTHORIZED, 456])
    def test_lyrics_are_saved_without_translation(
        self, plugin, module_helper, requests_mock, monkeypatch, status
    ):
        plugin.config["translate"].set({"api_key": "key", "to_language": "fr"})
        monkeypatch.setattr(
            plugin, "find_lyrics", lambda _item: Lyrics(GOOD_TEXT, "lrclib")
        )
        requests_mock.post(lyrics.Translator.TRANSLATE_URL, status_code=status)
        item = module_helper.add_item(
            title="Song",
            artist="Artist",
            lyrics="",
            lyrics_translation_language="FR",
        )

        plugin.add_item_lyrics(item, False)

        item = module_helper.lib.get_item(item.id)
        assert item.lyrics == GOOD_TEXT
        assert item.lyrics_backend == "lrclib"
        assert "lyrics_translation_language" not in item

    def test_invalid_configuration_still_stores_lyrics(
        self, plugin, module_helper, monkeypatch, caplog
    ):
        plugin.config["translate"].set({"provider": "nonsense"})
        monkeypatch.setattr(
            plugin, "find_lyrics", lambda _item: Lyrics(GOOD_TEXT, "lrclib")
        )
        item = module_helper.add_item(title="Song", artist="Artist", lyrics="")

        plugin.add_item_lyrics(item, False)

        assert module_helper.lib.get_item(item.id).lyrics == GOOD_TEXT
        assert "unknown translate.provider 'nonsense'" in caplog.text


def test_configuration_is_checked_when_the_command_starts(
    plugin, providers, monkeypatch, caplog
):
    """`beet lyrics` reports a bad translate setting before fetching."""
    plugin.config["translate"].set({"provider": "deepl"})
    (command,) = plugin.commands()
    options = command.parser.parse_args([])[0]
    monkeypatch.setattr(plugin, "add_item_lyrics", lambda *_: None)

    command.func(_FakeLibrary(), options, [])

    assert "translate.api_key and translate.to_language" in caplog.text


class _FakeLibrary:
    @staticmethod
    def items(_query):
        return [Item(title="Song", artist="Artist")]
