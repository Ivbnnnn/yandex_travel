from datetime import UTC, datetime, timedelta

from .base import BaseService, own, public


class NotificationService(BaseService):
    async def list(self, user_id):
        async with self.uow_factory() as uow:
            items = await uow.notifications.all(user_id=user_id)
            return {"items": [public(n) for n in reversed(items)]}

    async def read(self, user_id, notification_id):
        async with self.uow_factory() as uow:
            notification = own(await uow.notifications.get(notification_id), user_id)
            notification.read_at = datetime.now(UTC)
            await uow.commit()
            return public(notification)

    async def maintenance(self):
        async with self.uow_factory() as uow:
            await uow.bookings.expire_holds()
            for booking, user in await uow.bookings.reminders(self.today() + timedelta(days=1)):
                if not await uow.notifications.exists(booking.id, "booking_reminder"):
                    await uow.notifications.add(
                        user_id=user.id,
                        booking_id=booking.id,
                        type="booking_reminder",
                        message=f"Check-in tomorrow: {booking.snapshot['hotel_name']}",
                    )
            await uow.commit()


class AnalyticsService(BaseService):
    async def record(self, user_id, data):
        async with self.uow_factory() as uow:
            await uow.analytics.add(
                name=data.name,
                user_id=user_id,
                payload=data.model_dump(mode="json", exclude={"name"}),
            )
            await uow.commit()
