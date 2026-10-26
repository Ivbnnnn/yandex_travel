from datetime import UTC, datetime, timedelta

from ..errors import ConflictError, IdempotencyError, NotFoundError, SoldOutError, ValidationError
from .base import BaseService, fingerprint, own, public
from .catalog import free_stock


class BookingService(BaseService):
    async def create(self, user_id, data, key):
        async with self.uow_factory() as uow:
            # All mutating user operations lock user first, then room, then booking.
            await self.active_user(uow, user_id)
            existing = await uow.bookings.by_key(user_id, key)
            if existing:
                if existing.request_hash != fingerprint(data):
                    raise IdempotencyError()
                return public(existing)
            self.validate_dates(data.check_in, data.check_out)
            room = await uow.rooms.get(data.room_id, lock=True)
            hotel = await uow.hotels.get(data.hotel_id)
            rate = await uow.rates.get(data.rate_id)
            if (
                not room
                or not hotel
                or not rate
                or not hotel.is_active
                or not room.is_active
                or not rate.is_active
            ):
                raise NotFoundError("Hotel, room or rate not available")
            if room.hotel_id != hotel.id or rate.room_id != room.id:
                raise ValidationError("Hotel, room and rate do not match")
            if data.guests_count > room.capacity * data.rooms_count:
                raise ValidationError("Too many guests for the selected rooms")
            intervals = await uow.bookings.intervals([room.id], data.check_in, data.check_out)
            if free_stock(room.stock, data.check_in, data.check_out, intervals) < data.rooms_count:
                raise SoldOutError()
            total = rate.price * (data.check_out - data.check_in).days * data.rooms_count
            if total > 9999999999:
                raise ValidationError("Booking total exceeds the supported amount")
            booking = await uow.bookings.add(
                user_id=user_id,
                **data.model_dump(),
                total_price=total,
                currency=rate.currency,
                expires_at=datetime.now(UTC) + timedelta(seconds=self.settings.HOLD_TTL_SECONDS),
                idempotency_key=key,
                request_hash=fingerprint(data),
                snapshot={
                    "hotel_name": hotel.name,
                    "address": hotel.address,
                    "room_name": room.name,
                    "rate_name": rate.name,
                    "price_per_night": str(rate.price),
                    "cancellation_policy": rate.cancellation_policy,
                    "breakfast_included": rate.breakfast_included,
                    "conditions": rate.conditions,
                },
            )
            await uow.commit()
            return public(booking)

    async def get(self, user_id, booking_id):
        async with self.uow_factory() as uow:
            await uow.bookings.expire_holds()
            booking = own(await uow.bookings.get(booking_id), user_id)
            result = public(booking)
            result["payments"] = [public(p) for p in await uow.payments.all(booking_id=booking.id)]
            await uow.commit()
            return result

    async def list(self, user_id):
        async with self.uow_factory() as uow:
            await uow.bookings.expire_holds()
            result = [public(b) for b in await uow.bookings.all(user_id=user_id)]
            await uow.commit()
            return {"items": result}

    async def cancel(self, user_id, booking_id):
        async with self.uow_factory() as uow:
            await self.active_user(uow, user_id)
            initial = own(await uow.bookings.get(booking_id), user_id)
            await uow.rooms.get(initial.room_id, lock=True)
            booking = own(await uow.bookings.get(booking_id, lock=True), user_id)
            if booking.status == "cancelled":
                return public(booking)
            if booking.status == "confirmed" and booking.check_in <= self.today():
                raise ConflictError("Cancellation is only allowed before check-in")
            if booking.status == "confirmed" and not booking.snapshot.get("conditions", {}).get(
                "free_cancellation_before_check_in", True
            ):
                raise ConflictError("This rate does not allow cancellation after payment")
            booking.status = "cancelled"
            for payment in await uow.payments.all(booking_id=booking.id):
                if payment.status == "success":
                    payment.status = "refunded"
                elif payment.status == "pending":
                    payment.status = "failed"
            await uow.commit()
            return public(booking)


async def confirm_booking(uow, booking):
    booking.status = "confirmed"
    user = await uow.users.get(booking.user_id)
    if user.is_active and user.notifications_enabled:
        if not await uow.notifications.exists(booking.id, "booking_confirmation"):
            await uow.notifications.add(
                user_id=user.id,
                booking_id=booking.id,
                type="booking_confirmation",
                message=f"Booking {booking.id} confirmed: {booking.snapshot['hotel_name']}",
            )


class PaymentService(BaseService):
    def require_demo(self):
        if not self.settings.DEMO_PAYMENTS:
            raise ConflictError("No real payment provider configured; demo payments are disabled")

    async def create(self, user_id, data, key):
        self.require_demo()
        async with self.uow_factory() as uow:
            await self.active_user(uow, user_id)
            existing = await uow.payments.by_key(user_id, key)
            if existing:
                if existing.request_hash != fingerprint(data):
                    raise IdempotencyError()
                return public(existing)
            initial = own(await uow.bookings.get(data.booking_id), user_id)
            await uow.rooms.get(initial.room_id, lock=True)
            booking = own(await uow.bookings.get(data.booking_id, lock=True), user_id)
            if booking.status != "pending" or booking.expires_at <= datetime.now(UTC):
                raise ConflictError("Booking cannot be paid or reservation has expired")
            previous = await uow.payments.all(booking_id=booking.id)
            if any(p.status in ("pending", "success") for p in previous):
                raise ConflictError("A payment is already in progress for this booking")
            payment = await uow.payments.add(
                user_id=user_id,
                booking_id=booking.id,
                amount=booking.total_price,
                idempotency_key=key,
                request_hash=fingerprint(data),
                status="pending",
                demo_ready_at=(
                    datetime.now(UTC) + timedelta(seconds=2)
                    if data.payment_token == "timeout"
                    else None
                ),
            )
            if data.payment_token == "success":
                payment.status = "success"
                await confirm_booking(uow, booking)
            elif data.payment_token == "fail":
                payment.status = "failed"
                # Keep the hold until its deadline so a failed payment may be retried.
            await uow.commit()
            return public(payment)

    async def get(self, user_id, payment_id):
        async with self.uow_factory() as uow:
            await self.active_user(uow, user_id)
            initial = own(await uow.payments.get(payment_id), user_id)
            initial_booking = await uow.bookings.get(initial.booking_id)
            await uow.rooms.get(initial_booking.room_id, lock=True)
            booking = await uow.bookings.get(initial.booking_id, lock=True)
            payment = own(await uow.payments.get(payment_id, lock=True), user_id)
            if (
                payment.status == "pending"
                and payment.demo_ready_at
                and payment.demo_ready_at <= datetime.now(UTC)
            ):
                if booking.status != "pending" or booking.expires_at <= datetime.now(UTC):
                    payment.status = "failed"
                else:
                    payment.status = "success"
                    await confirm_booking(uow, booking)
            await uow.commit()
            return public(payment)
