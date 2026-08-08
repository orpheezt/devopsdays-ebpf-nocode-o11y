from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Request

from .config import SettingsSection

ExceptionHandler = Callable[[Request, Any], Any]


@dataclass(frozen=True)
class Module:
    name: str
    router: APIRouter
    settings: type[SettingsSection]
    exception_handlers: Mapping[type[Exception], ExceptionHandler] = field(
        default_factory=dict
    )
