"""
Базовый класс для работы с API (асинхронная версия на httpx).

История исправлений оригинала из репозитория
https://github.com/sadboy2001/api_testing :

1. Бесконечный цикл while: успехом теперь считается весь диапазон 200-299.
2. Тело запроса уходит как JSON (json=json_body), а не как form-данные.
3. Есть timeout, задаётся при создании объекта.
4. Возвращается объект Response целиком, а не response.json()['message'].
5. Код не выполняется при импорте: демонстрация под __main__.
6. Логирование не падает на не-JSON ответе.

Что добавлено в асинхронной версии:
7. Все методы async: вызываются через await.
8. Повтор запроса при обрыве соединения (petstore иногда рвёт связь).
9. Соединения не переиспользуются: сервер обрывает простаивающие.

Использование:
    async with BaseRequest(BASE_URL) as api:
        response = await api.get('store/inventory')
"""
import asyncio
import json
import pprint

import allure
import httpx

BASE_URL = 'https://petstore.swagger.io/v2'


class BaseRequest:
    """Асинхронная обёртка над httpx с проверкой кодов и логированием."""

    def __init__(self, base_url, timeout=10, retries=3):
        # rstrip убирает лишний слеш, чтобы не было двойных
        self.base_url = base_url.rstrip('/')
        self.retries = retries
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={'Content-Type': 'application/json'},
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=0),
        )

    # --- async with BaseRequest(BASE_URL) as api: ... ---------------

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        await self.close()

    async def close(self):
        await self.client.aclose()

    # --- внутренняя часть -------------------------------------------

    def _url(self, path):
        return f"{self.base_url}/{path.lstrip('/')}"

    async def _send(self, method, path, json_body=None):
        """Отправляет запрос; при обрыве соединения повторяет."""
        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                return await self.client.request(
                    method, self._url(path), json=json_body
                )
            except (httpx.RemoteProtocolError, httpx.ConnectError,
                    httpx.ReadError) as error:
                last_error = error
                await asyncio.sleep(0.3 * attempt)
        raise last_error

    async def _request(self, method, path, json_body=None,
                       expected_error=False):
        with allure.step(f'{method} {path}'):
            if json_body is not None:
                allure.attach(
                    json.dumps(json_body, ensure_ascii=False, indent=2),
                    name='Тело запроса',
                    attachment_type=allure.attachment_type.JSON,
                )

            response = await self._send(method, path, json_body)

            self._log(method, response)
            allure.attach(
                f'status: {response.status_code}\n\n{response.text[:2000]}',
                name='Ответ',
                attachment_type=allure.attachment_type.TEXT,
            )
            self._check(response, expected_error)
            return response

    @staticmethod
    def _check(response, expected_error):
        """Проверяет код ответа. Успех это 200-299."""
        code = response.status_code

        if expected_error:
            assert code >= 400, (
                f'Ждали ошибку, но получили {code}: {response.text[:200]}'
            )
        else:
            assert 200 <= code < 300, (
                f'Ждали успех, но получили {code}: {response.text[:200]}'
            )

    @staticmethod
    def _log(method, response):
        """Печатает, что произошло. Не падает, если ответ не JSON."""
        pprint.pprint('-' * 50)
        pprint.pprint(f'{method} {response.url}')
        pprint.pprint(f'status: {response.status_code}')

        try:
            pprint.pprint(response.json())
        except ValueError:
            pprint.pprint(response.text[:200])

    # --- публичные методы (CRUD) ------------------------------------

    async def get(self, path, expected_error=False):
        return await self._request('GET', path, expected_error=expected_error)

    async def post(self, path, json_body):
        return await self._request('POST', path, json_body=json_body)

    async def put(self, path, json_body):
        return await self._request('PUT', path, json_body=json_body)

    async def delete(self, path, expected_error=False):
        return await self._request(
            'DELETE', path, expected_error=expected_error
        )

    async def delete_quiet(self, path):
        """Удаляет объект, не проверяя код ответа.

        Нужен для уборки за собой: объекта может уже не быть.
        Уборку не проверяют, а просто выполняют, и она не роняет тест,
        даже если сервер недоступен.
        """
        with allure.step(f'Уборка: DELETE {path}'):
            try:
                response = await self._send('DELETE', path)
            except httpx.HTTPError:
                return None
            self._log('DELETE', response)
            return response


async def _demo():
    print('Проверяем, что API отвечает:')
    async with BaseRequest(BASE_URL) as api:
        answer = await api.get('pet/findByStatus?status=available')
        print('Питомцев доступно:', len(answer.json()))


if __name__ == '__main__':
    # Не выполнится при импорте файла тестами.
    asyncio.run(_demo())