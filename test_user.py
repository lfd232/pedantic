
import allure
import pytest
from base_request import BASE_URL, BaseRequest
from models import ApiResponse, User

base_request = BaseRequest(BASE_URL)


@pytest.fixture
def new_user():
    user = User()  # id и username сгенерированы автоматически
    yield user
    base_request.delete_quiet(f'user/{user.username}')


@allure.feature('User')
@allure.story('Создание пользователя')
@allure.title('POST: пользователь создаётся')
def test_create_user(new_user):
    response = base_request.post('user', new_user.payload())

    body = ApiResponse.model_validate(response.json())
    assert body.code == 200
    assert body.message == str(new_user.id)


@allure.feature('User')
@allure.story('Чтение пользователя')
@allure.title('GET: пользователь читается после создания')
def test_read_user_after_create(new_user):
    base_request.post('user', new_user.payload())

    response = base_request.get(f'user/{new_user.username}')

    actual = User.model_validate(response.json())
    assert actual == new_user


@allure.feature('User')
@allure.story('Обновление пользователя')
@allure.title('PUT: имя пользователя меняется')
def test_update_user(new_user):
    base_request.post('user', new_user.payload())

    # копия модели с изменённым полем
    updated = new_user.model_copy(update={'first_name': 'Пётр'})
    base_request.put(f'user/{new_user.username}', updated.payload())

    response = base_request.get(f'user/{new_user.username}')
    actual = User.model_validate(response.json())
    assert actual.first_name == 'Пётр'


@allure.feature('User')
@allure.story('Обновление пользователя')
@allure.title('Обновление не затрагивает других пользователей')
def test_update_does_not_touch_others(new_user):
    other = User()
    try:
        base_request.post('user', new_user.payload())
        base_request.post('user', other.payload())

        updated = new_user.model_copy(update={'first_name': 'Пётр'})
        base_request.put(f'user/{new_user.username}', updated.payload())

        response = base_request.get(f'user/{other.username}')
        actual = User.model_validate(response.json())
        assert actual == other
    finally:
        base_request.delete_quiet(f'user/{other.username}')

