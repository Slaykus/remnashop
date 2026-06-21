from pathlib import Path

from fluent_compiler.bundle import FluentBundle
from fluentogram.storage.base import BaseStorage
from fluentogram.translator import FluentTranslator


class LayeredFileStorage(BaseStorage):
    def __init__(
        self,
        user_translations_dir: Path,
        default_translations_dir: Path,
        use_isolating: bool = False,
    ) -> None:
        super().__init__()
        self._user_dir = user_translations_dir
        self._default_dir = default_translations_dir
        self._use_isolating = use_isolating
        self._custom_translators: dict[str, FluentTranslator] = {}
        self._default_translators: dict[str, FluentTranslator] = {}
        self._load_translations()

    def _make_translator(self, locale: str, texts: list[str]) -> FluentTranslator:
        return FluentTranslator(
            locale=locale,
            translator=FluentBundle.from_string(  # type: ignore[no-untyped-call]
                locale=locale,
                text="\n".join(texts),
                use_isolating=self._use_isolating,
            ),
        )

    @staticmethod
    def _sorted_ftl_texts(locale_dir: Path) -> list[str]:
        # Load all .ftl files with custom.ftl last so its definitions win over
        # any same-named messages in other files (e.g. frg-user in utils.ftl).
        all_files = sorted(locale_dir.rglob("*.ftl"))
        non_custom = [f for f in all_files if f.name != "custom.ftl"]
        custom_files = [f for f in all_files if f.name == "custom.ftl"]
        return [f.read_text("utf8") for f in non_custom + custom_files]

    def _load_translations(self) -> None:
        # Local dev fallback: assets.default/ not present — behave like FileStorage
        if not self._default_dir.exists():
            for locale_dir in self._user_dir.iterdir():
                if not locale_dir.is_dir():
                    continue
                locale = locale_dir.name
                texts = self._sorted_ftl_texts(locale_dir)
                if texts:
                    translator = self._make_translator(locale, texts)
                    self._default_translators[locale] = translator
                    self.add_translator(translator)
            return

        for locale_dir in self._default_dir.iterdir():
            if not locale_dir.is_dir():
                continue
            locale = locale_dir.name

            # Load all default .ftl files, custom.ftl last so it takes priority
            default_texts = self._sorted_ftl_texts(locale_dir)
            if default_texts:
                translator = self._make_translator(locale, default_texts)
                self._default_translators[locale] = translator
                self.add_translator(translator)

            # Load user's custom.ftl (optional)
            custom_ftl = self._user_dir / locale / "custom.ftl"
            if custom_ftl.exists():
                text = custom_ftl.read_text("utf8")
                self._custom_translators[locale] = self._make_translator(locale, [text])

    def get_translators_for_language(self, language: str) -> list[FluentTranslator]:
        locale_chain = self._locales_map.get(language, (language,))
        result: list[FluentTranslator] = []
        for locale in locale_chain:
            if locale in self._custom_translators:
                result.append(self._custom_translators[locale])
            if locale in self._default_translators:
                result.append(self._default_translators[locale])
        return result

    async def close(self) -> None:
        pass
