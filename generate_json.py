"""Создаёт JSON-файлы средствами Pydantic.

Запуск (из папки api_testing):
    python generate_json.py
"""
from pathlib import Path

from pydantic_core import to_json

from models import Order, User

OUT_DIR = Path(__file__).parent / 'json_data'


if __name__ == '__main__':
    # 1. Файлы с данными: JSON делает model_dump_json внутри save_json
    print(User().save_json(OUT_DIR / 'user.json'))
    print(Order().save_json(OUT_DIR / 'order.json'))

    # 2. JSON-схемы: тоже средствами Pydantic (to_json из pydantic_core)
    for name, model in (('user', User), ('order', Order)):
        schema = model.model_json_schema(by_alias=True)
        path = OUT_DIR / f'{name}_schema.json'
        path.write_bytes(to_json(schema, indent=2))
        print(path)

    # 3. Проверка: читаем файл обратно в модель
    user = User.load_json(OUT_DIR / 'user.json')
    print('Прочитано из файла:', user)