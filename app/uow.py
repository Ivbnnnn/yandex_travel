from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from . import repositories as r


class UnitOfWork:
    """One application operation = one session and transaction.

    Writes explicitly call commit(). Uncommitted work always rolls back.
    Repositories are created together and share this session.
    """

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def __aenter__(self):
        self.session = self.sessions()
        self.users = r.UserRepository(self.session)
        self.sessions_repo = r.SessionRepository(self.session)
        self.hotels = r.HotelRepository(self.session)
        self.rooms = r.RoomRepository(self.session)
        self.rates = r.RateRepository(self.session)
        self.bookings = r.BookingRepository(self.session)
        self.payments = r.PaymentRepository(self.session)
        self.favorites = r.FavoriteRepository(self.session)
        self.photos = r.PhotoRepository(self.session)
        self.filters = r.FilterRepository(self.session)
        self.reviews = r.ReviewRepository(self.session)
        self.notifications = r.NotificationRepository(self.session)
        self.analytics = r.AnalyticsRepository(self.session)
        await self.session.begin()
        return self

    async def commit(self):
        await self.session.commit()

    async def __aexit__(self, exc_type, exc, traceback):
        try:
            await self.session.rollback()
        finally:
            await self.session.close()


UowFactory = Callable[[], UnitOfWork]
