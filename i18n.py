"""
Internationalization support for Fanbox Monitor.
"""
import locale
from typing import Dict, Optional

# Translation strings
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "error_title": "Fanbox Monitor Runtime Error",
        "supporting_title": "{creator_name} you support has an update!",
        "following_title": "{creator_name} you follow has an update!",
        "config_load_error": "Failed to load configuration",
        "detection_error": "Detection error",
        "runtime_error": "Runtime error",
    },
    "zh": {
        "error_title": "Fanbox 监听器运行错误",
        "supporting_title": "你赞助的{creator_name}有更新！",
        "following_title": "你关注的{creator_name}有更新！",
        "config_load_error": "加载配置失败",
        "detection_error": "检测时发生错误",
        "runtime_error": "运行时发生错误",
    },
    "zh-tw": {
        "error_title": "Fanbox 監聽器運行錯誤",
        "supporting_title": "你贊助的{creator_name}有更新！",
        "following_title": "你關注的{creator_name}有更新！",
        "config_load_error": "載入配置失敗",
        "detection_error": "檢測時發生錯誤",
        "runtime_error": "運行時發生錯誤",
    },
    "ja": {
        "error_title": "Fanbox モニター実行エラー",
        "supporting_title": "あなたが支援している{creator_name}に更新があります！",
        "following_title": "あなたがフォローしている{creator_name}に更新があります！",
        "config_load_error": "設定の読み込みに失敗しました",
        "detection_error": "検出中にエラーが発生しました",
        "runtime_error": "実行中にエラーが発生しました",
    },
    "ko": {
        "error_title": "Fanbox 모니터 런타임 오류",
        "supporting_title": "후원하는 {creator_name}에 업데이트가 있습니다!",
        "following_title": "팔로우하는 {creator_name}에 업데이트가 있습니다!",
        "config_load_error": "구성 로드 실패",
        "detection_error": "검색 중 오류 발생",
        "runtime_error": "런타임 오류 발생",
    },
}

# Default language
DEFAULT_LANG = "en"

# Supported languages
SUPPORTED_LANGS = list(TRANSLATIONS.keys())


def detect_language() -> str:
    """
    Detect system language.
    Returns language code (en, zh, zh-tw, ja, ko).
    """
    try:
        lang, _ = locale.getdefaultlocale()
        if lang:
            lang = lang.lower()
            # Map locale to language code
            if lang.startswith("zh"):
                if "tw" in lang or "hk" in lang:
                    return "zh-tw"
                return "zh"
            elif lang.startswith("ja"):
                return "ja"
            elif lang.startswith("ko"):
                return "ko"
    except Exception:
        pass
    return DEFAULT_LANG


def get_language(config_lang: Optional[str] = None) -> str:
    """
    Get language code from config or system.
    :param config_lang: Language code from config file
    :return: Language code
    """
    if config_lang and config_lang in SUPPORTED_LANGS:
        return config_lang
    return detect_language()


def translate(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """
    Translate a key to the specified language.
    :param key: Translation key
    :param lang: Language code
    :param kwargs: Format arguments
    :return: Translated string
    """
    if lang not in TRANSLATIONS:
        lang = DEFAULT_LANG
    
    translations = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
    text = translations.get(key, key)
    
    # Format with kwargs if provided
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    
    return text

