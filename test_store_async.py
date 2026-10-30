import allure
import pytest
from async_request import AsyncBaseRequest
from models import Order


@pytest.fixture
async def api():
    async with AsyncBaseRequest() as client:
        yield client


@pytest.fixture
async def created_order(api):
    order = Order()
    await api.post('store/order', order.payload())
    yield order
    await api.delete_quiet(f'store/order/{order.id}')


@allure.feature('Store (async)')
@allure.title('POST: заказ создаётся')
async def test_create_order(api):
    order = Order()
    try:
        response = await api.post('store/order', order.payload())
        assert Order.model_validate(response.json()) == order
    finally:
        await api.delete_quiet(f'store/order/{order.id}')


@allure.feature('Store (async)')
@allure.title('GET: заказ можно получить по id')
async def test_get_order(api, created_order):
    response = await api.get(f'store/order/{created_order.id}')
    assert Order.model_validate(response.json()).id == created_order.id


@allure.feature('Store (async)')
@allure.title('Поля заказа сохранились без изменений')
async def test_order_saved_unchanged(api, created_order):
    response = await api.get(f'store/order/{created_order.id}')
    assert Order.model_validate(response.json()) == created_order


@allure.feature('Store (async)')
@allure.title('DELETE: заказ удаляется')
async def test_delete_order(api, created_order):
    await api.delete(f'store/order/{created_order.id}')

    after = await api.get(
        f'store/order/{created_order.id}', expected_error=True
    )
    assert after.status_code == 404