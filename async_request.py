"""Асинхронная версия BaseRequest на httpx.

Логика та же, что в base_request.py: успех это 200-299,
expected_error=True ждёт ошибку, delete_quiet ничего не проверяет.
Отличие: все методы нужно вызывать через await.
"""
import asyncio
import json
import pprint

import allure
import httpx

BASE_URL = 'https://petstore.swagger.io/v2'


class AsyncBaseRequest:
    def __init__(self, base_url=BASE_URL, timeout=10, retries=3):
        self.base_url = base_url.rstrip('/')
        self.retries = retries
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={'Content-Type': 'application/json'},
            follow_redirects=True,
            # не переиспользуем соединения: petstore обрывает простаивающие,
            # из-за этого и было "Server disconnected"
            limits=httpx.Limits(max_keepalive_connections=0),
        )

    # --- async with AsyncBaseRequest() as api: ... ------------------

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
        """Уборка: удаляет объект и не проверяет код ответа."""
        with allure.step(f'Уборка: DELETE {path}'):
            try:
                response = await self._send('DELETE', path)
            except httpx.HTTPError:
                # уборка не должна ронять тест, даже если сервер недоступен
                return None
            self._log('DELETE', response)
            return response