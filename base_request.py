"""
Базовый класс для работы с API.

Это исправленная версия файла из репозитория
https://github.com/sadboy2001/api_testing

Оригинал содержал ошибки, которые нужно знать:

1. Бесконечный цикл while
   Было: while not stop_flag, выход только при status_code == 200
   Проблема: любой успешный ответ 201 или 204 крутит цикл вечно.
   Теперь успехом считается весь диапазон 200-299.

2. Тело запроса уходило не как JSON
   Было: requests.post(url, data=data)
   Проблема: словарь уходит form-кодированным, а не JSON.
   Теперь: requests.request(..., json=json_body)

3. Не было timeout
   Проблема: при зависшем API тест висит молча.
   Теперь timeout задаётся при создании объекта.

4. response.json()['message']
   Проблема: KeyError, если в ответе нет поля message.
   Теперь возвращается объект Response целиком.

5. Код выполнялся при импорте
   Было: вызовы get и post в конце файла без защиты.
   Теперь демонстрация под if __name__ == '__main__'.

6. Логирование response.json() падало на не-JSON ответе
   Теперь ответ читается через try.
"""

import json
import pprint

import allure
import requests

BASE_URL = 'https://petstore.swagger.io/v2'


class BaseRequest:
    """Обёртка над requests с проверкой кодов ответа и логированием."""

    def __init__(self, base_url, timeout=15):
        # rstrip убирает лишний слеш, чтобы не было двойных
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def _request(self, method, path, json_body=None, expected_error=False):
        url = f"{self.base_url}/{path.lstrip('/')}"

        with allure.step(f'{method} {path}'):
            if json_body is not None:
                allure.attach(
                    json.dumps(json_body, ensure_ascii=False, indent=2),
                    name='Тело запроса',
                    attachment_type=allure.attachment_type.JSON,
                )

            response = self.session.request(
                method,
                url,
                json=json_body,
                timeout=self.timeout,
            )

            self._log(method, response)
            self._attach_response(response)
            self._check(response, expected_error)
            return response

    def _check(self, response, expected_error):
        """Проверяет код ответа. Успех — это 200-299."""
        code = response.status_code

        if expected_error:
            assert code >= 400, (
                f'Ждали ошибку, но получили {code}: {response.text[:200]}'
            )
        else:
            assert 200 <= code < 300, (
                f'Ждали успех, но получили {code}: {response.text[:200]}'
            )

    def _attach_response(self, response):
        """Прикладывает ответ к отчёту Allure."""
        allure.attach(
            f'{response.request.method} {response.url}\n'
            f'status: {response.status_code}\n\n{response.text[:2000]}',
            name='Ответ',
            attachment_type=allure.attachment_type.TEXT,
        )

    def _log(self, method, response):
        """Печатает, что произошло. Не падает, если ответ не JSON."""
        pprint.pprint('-' * 50)
        pprint.pprint(f'{method} {response.url}')
        pprint.pprint(f'status: {response.status_code}')

        try:
            pprint.pprint(response.json())
        except ValueError:
            pprint.pprint(response.text[:200])

    # --- публичные методы -------------------------------------------

    def get(self, path, expected_error=False):
        return self._request('GET', path, expected_error=expected_error)

    def post(self, path, json_body):
        return self._request('POST', path, json_body=json_body)

    def put(self, path, json_body):
        return self._request('PUT', path, json_body=json_body)

    def delete(self, path, expected_error=False):
        return self._request('DELETE', path, expected_error=expected_error)

    def delete_quiet(self, path):
        """Удаляет объект, не проверяя код ответа.

        Нужен для уборки за собой. Объекта может уже не быть:
        тест успел его удалить сам, или тест упал раньше,
        чем что-то создал.

        Обычный delete здесь не годится. expected_error=True
        требует ошибки, а если объект ещё есть, сервер
        вернёт 200 и проверка упадёт.

        Подсказка: уборку не проверяют, а просто выполняют.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"

        with allure.step(f'Уборка: DELETE {path}'):
            response = self.session.request(
                'DELETE',
                url,
                timeout=self.timeout,
            )

            self._log('DELETE', response)
            return response


base_request = BaseRequest(BASE_URL)


if __name__ == '__main__':
    # Этот блок не выполнится при импорте файла тестами.
    # pytest подхватит только функции с именем test_.
    print('Проверяем, что API отвечает:')
    answer = base_request.get('pet/findByStatus?status=available')
    print('Питомцев доступно:', len(answer.json()))