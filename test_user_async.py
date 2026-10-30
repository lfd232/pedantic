import asyncio

import allure
import pytest
from async_request import AsyncBaseRequest
from models import ApiResponse, User


@pytest.fixture
async def api():
    async with AsyncBaseRequest() as client:
        yield client


@pytest.fixture
async def new_user(api):
    user = User()
    yield user
    await api.delete_quiet(f'user/{user.username}')


@allure.feature('User (async)')
@allure.title('POST: пользователь создаётся')
async def test_create_user(api, new_user):
    response = await api.post('user', new_user.payload())

    body = ApiResponse.model_validate(response.json())
    assert body.code == 200
    assert body.message == str(new_user.id)


@allure.feature('User (async)')
@allure.title('GET: пользователь читается после создания')
async def test_read_user_after_create(api, new_user):
    await api.post('user', new_user.payload())

    response = await api.get(f'user/{new_user.username}')
    assert User.model_validate(response.json()) == new_user


@allure.feature('User (async)')
@allure.title('PUT: имя пользователя меняется')
async def test_update_user(api, new_user):
    await api.post('user', new_user.payload())

    updated = new_user.model_copy(update={'first_name': 'Пётр'})
    await api.put(f'user/{new_user.username}', updated.payload())

    response = await api.get(f'user/{new_user.username}')
    assert User.model_validate(response.json()).first_name == 'Пётр'


@allure.feature('User (async)')
@allure.title('Обновление не затрагивает других пользователей')
async def test_update_does_not_touch_others(api, new_user):
    other = User()
    try:
        # два POST выполняются одновременно
        await asyncio.gather(
            api.post('user', new_user.payload()),
            api.post('user', other.payload()),
        )

        updated = new_user.model_copy(update={'first_name': 'Пётр'})
        await api.put(f'user/{new_user.username}', updated.payload())

        response = await api.get(f'user/{other.username}')
        assert User.model_validate(response.json()) == other
    finally:
        await api.delete_quiet(f'user/{other.username}')