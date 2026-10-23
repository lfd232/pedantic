"""Pydantic-модели для petstore.swagger.io.

Одна модель решает две задачи:
1. Автогенерация JSON для запроса: Order().payload()
2. Валидация ответа сервера:        Order.model_validate(response.json())
"""
import random
import re
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FIRST_ID = 900_000
LAST_ID = 999_999


def _random_id() -> int:
    return random.randint(FIRST_ID, LAST_ID)


def _random_username() -> str:
    tail = ''.join(random.choices(string.ascii_lowercase, k=8))
    return f'qa_{tail}'


class ApiModel(BaseModel):
    """Общая база: поля в Python snake_case, в JSON camelCase."""

    # populate_by_name: можно создавать и по имени поля, и по alias
    model_config = ConfigDict(populate_by_name=True)

    def payload(self) -> dict:
        """Готовый JSON-словарь для тела запроса."""
        return self.model_dump(by_alias=True, mode='json')

    def to_json(self) -> str:
        """JSON-строка, которую делает сам Pydantic."""
        return self.model_dump_json(by_alias=True, indent=2)

    def save_json(self, path) -> Path:
        """Сохраняет модель в JSON-файл (содержимое делает Pydantic)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding='utf-8')
        return path

    @classmethod
    def load_json(cls, path):
        """Читает JSON-файл обратно в модель с валидацией."""
        return cls.model_validate_json(Path(path).read_text(encoding='utf-8'))


class Order(ApiModel):
    id: int = Field(default_factory=_random_id)
    pet_id: int = Field(default=1, alias='petId')
    quantity: int = Field(default=1, ge=1)
    ship_date: datetime = Field(
        default_factory=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
        alias='shipDate',
    )
    status: Literal['placed', 'approved', 'delivered'] = 'placed'
    complete: bool = True

    @field_validator('ship_date', mode='before')
    @classmethod
    def _fix_tz(cls, value):
        # сервер отдаёт '2026-01-01T00:00:00.000+0000' (без двоеточия
        # в часовом поясе), приводим к '+00:00'
        if isinstance(value, str):
            return re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', value)
        return value


class User(ApiModel):
    id: int = Field(default_factory=_random_id)
    username: str = Field(default_factory=_random_username)
    first_name: str = Field(default='Иван', alias='firstName')
    last_name: str = Field(default='Петров', alias='lastName')
    email: str = 'ivan@example.com'
    password: str = 'secret'
    phone: str = '8999999999'
    user_status: int = Field(default=1, alias='userStatus')


class ApiResponse(ApiModel):
    """Ответ на POST/PUT/DELETE: {"code": 200, "type": "unknown", "message": "..."}"""
    code: int
    type: str
    message: str