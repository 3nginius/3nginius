from revsearch.providers.base import Provider, SearchHit, SearchResult
from revsearch.providers.yandex import YandexProvider
from revsearch.providers.tineye import TinEyeProvider
from revsearch.providers.serpapi_lens import SerpAPIGoogleLensProvider
from revsearch.providers.bing import BingVisualProvider

__all__ = [
    "Provider",
    "SearchHit",
    "SearchResult",
    "YandexProvider",
    "TinEyeProvider",
    "SerpAPIGoogleLensProvider",
    "BingVisualProvider",
    "all_providers",
]


def all_providers():
    return [
        YandexProvider(),
        TinEyeProvider(),
        SerpAPIGoogleLensProvider(),
        BingVisualProvider(),
    ]
