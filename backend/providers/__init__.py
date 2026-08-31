from backend.providers.base import SearchProvider
from backend.providers.demo import DemoProvider

PROVIDERS: list[SearchProvider] = [
    DemoProvider(),
]
