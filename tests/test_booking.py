from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect


APPLICANT_NAME = "Анна Тестова"
VALIDATION_ERROR = "Проверьте, пожалуйста, заполнение формы."
BOOKING_CREATED = "Бронирование создано."


@pytest.fixture
def booking_page(page: Page, base_url: str) -> Page:
    response = page.goto(base_url, wait_until="domcontentloaded")
    if response is None or not response.ok:
        pytest.fail(f"Страница бронирования недоступна: {base_url}")
    return page


def submit_booking(
    page: Page, booking_date: str, *, end_time: str = "11:00", participants: str = "4"
) -> None:
    page.get_by_label("Переговорная").select_option("small")
    page.get_by_label("Дата").fill(booking_date)
    page.get_by_label("Начало").fill("10:00")
    page.get_by_label("Окончание").fill(end_time)
    page.get_by_label("Участники").fill(participants)
    page.get_by_label("Ваше имя").fill(APPLICANT_NAME)
    page.get_by_label("Рабочая почта").fill("anna@example.com")
    page.get_by_role("button", name="Забронировать", exact=True).click()


def test_successful_booking(booking_page: Page):
    booking_date = (date.today() + timedelta(days=2)).isoformat()
    submit_booking(booking_page, booking_date)

    status = booking_page.get_by_role("status")
    expect(status).to_be_visible()
    expect(status).to_contain_text(BOOKING_CREATED)
    expect(status).to_contain_text(
        f"Малая, {booking_date}, 10:00–11:00 · {APPLICANT_NAME}"
    )


def test_rejects_booking_over_room_capacity(booking_page: Page):
    booking_date = (date.today() + timedelta(days=2)).isoformat()
    submit_booking(booking_page, booking_date, participants="5")

    expect(booking_page.get_by_role("status")).to_have_text(VALIDATION_ERROR)
    expect(booking_page.get_by_text("В комнате максимум 4 участника.")).to_be_visible()


@pytest.mark.xfail(
    strict=True,
    reason="BUG-01: форма принимает бронь длительностью меньше 30 минут",
    raises=AssertionError,
)
def test_rejects_booking_shorter_than_30_minutes(booking_page: Page):
    booking_date = (date.today() + timedelta(days=2)).isoformat()
    submit_booking(booking_page, booking_date, end_time="10:29")

    status = booking_page.get_by_role("status")
    status.wait_for(state="visible")
    message = status.inner_text()
    if message != VALIDATION_ERROR and not message.startswith(BOOKING_CREATED):
        pytest.fail(f"Неожиданный ответ формы: {message!r}")
    assert message == VALIDATION_ERROR, f"Бронь на 29 минут должна отклоняться: {message!r}"
