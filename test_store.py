
import allure
import pytest
from base_request import BASE_URL, BaseRequest
from models import Order

base_request = BaseRequest(BASE_URL)


@pytest.fixture
def created_order():
    order = Order()  # id и остальные поля сгенерированы
    base_request.post('store/order', order.payload())
    yield order
    base_request.delete_quiet(f'store/order/{order.id}')


@allure.feature('Store')
@allure.story('Создание заказа')
@allure.title('POST: заказ создаётся')
def test_create_order():
    order = Order()
    try:
        response = base_request.post('store/order', order.payload())

        # model_validate упадёт с понятной ошибкой, если ответ не по схеме
        created = Order.model_validate(response.json())
        assert created == order
    finally:
        base_request.delete_quiet(f'store/order/{order.id}')


@allure.feature('Store')
@allure.story('Чтение заказа')
@allure.title('GET: заказ можно получить по id')
def test_get_order(created_order):
    response = base_request.get(f'store/order/{created_order.id}')

    actual = Order.model_validate(response.json())
    assert actual.id == created_order.id


@allure.feature('Store')
@allure.story('Чтение заказа')
@allure.title('Поля заказа сохранились без изменений')
def test_order_saved_unchanged(created_order):
    response = base_request.get(f'store/order/{created_order.id}')

    actual = Order.model_validate(response.json())
    assert actual == created_order


@allure.feature('Store')
@allure.story('Удаление заказа')
@allure.title('DELETE: заказ удаляется')
def test_delete_order(created_order):
    base_request.delete(f'store/order/{created_order.id}')

    after = base_request.get(
        f'store/order/{created_order.id}', expected_error=True
    )
    assert after.status_code == 404

