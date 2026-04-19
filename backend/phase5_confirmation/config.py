"""Configuration for Phase 5 — Confirmation."""

# Confirmation message templates
BOOKING_CONFIRMATION_TEMPLATE = (
    "Your appointment has been successfully booked!\n\n"
    "Booking Code: {booking_code}\n"
    "Date: {date}\n"
    "Time: {time}"
)

CANCELLATION_CONFIRMATION_TEMPLATE = (
    "Your appointment has been successfully cancelled.\n\n"
    "Booking Code: {booking_code}\n"
    "Was scheduled for: {scheduled_datetime}"
)

BOOKING_FAILURE_MESSAGE = "I'm sorry, but I couldn't complete your booking. Please try again."

CANCELLATION_FAILURE_MESSAGE = "I'm sorry, but I couldn't complete the cancellation. Please try again."
