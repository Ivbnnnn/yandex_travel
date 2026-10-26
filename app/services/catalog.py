from collections import defaultdict
from datetime import date
from decimal import Decimal

from ..errors import ConflictError, NotFoundError, ValidationError
from .base import BaseService, own, public


def free_stock(stock: int, start: date, end: date, intervals) -> int:
    """Peak occupied stock, not a sum of bookings on different nights."""
    events = defaultdict(int)
    for _, check_in, check_out, quantity in intervals:
        events[max(start, check_in)] += quantity
        events[min(end, check_out)] -= quantity
    occupied = peak = 0
    for day in sorted(events):
        occupied += events[day]
        peak = max(peak, occupied)
    return max(0, stock - peak)


class CatalogService(BaseService):
    async def compare(self, hotel_ids):
        from ..schemas import SearchQuery

        if len(set(hotel_ids)) != len(hotel_ids):
            raise ValidationError("Select two or three different hotels")
        return {"items": [await self.hotel(id, SearchQuery()) for id in hotel_ids]}

    async def _validate_codes(self, uow, styles, purposes):
        options = await uow.filters.all()
        for kind, requested in (("interior_style", styles), ("booking_purpose", purposes)):
            valid = {item.code for item in options if item.kind == kind}
            if set(requested) - valid:
                raise ValidationError(
                    f"Unknown {kind}: {', '.join(sorted(set(requested) - valid))}"
                )

    async def filters(self):
        async with self.uow_factory() as uow:
            options = await uow.filters.all()
            return {
                "interior_styles": [public(o) for o in options if o.kind == "interior_style"],
                "booking_purposes": [public(o) for o in options if o.kind == "booking_purpose"],
            }

    async def search(self, params):
        self.validate_dates(params.check_in, params.check_out)
        async with self.uow_factory() as uow:
            await self._validate_codes(uow, params.interior_style, params.booking_purpose)
            rows = await uow.rooms.candidates(params)
            occupied = defaultdict(list)
            if params.check_in:
                for interval in await uow.bookings.intervals(
                    [room.id for room, _, _ in rows], params.check_in, params.check_out
                ):
                    occupied[interval[0]].append(interval)
            hotels = {}
            for room, hotel, price in rows:
                if (
                    params.check_in
                    and free_stock(room.stock, params.check_in, params.check_out, occupied[room.id])
                    < params.rooms_count
                ):
                    continue
                item = hotels.get(hotel.id)
                if item is None:
                    photos = await uow.photos.all(hotel_id=hotel.id)
                    hotels[hotel.id] = {
                        **public(hotel),
                        "min_price": price,
                        "currency": "RUB",
                        "preview_photo_url": photos[0].url if photos else None,
                    }
                elif price < item["min_price"]:
                    item["min_price"] = price
            items = list(hotels.values())
            if params.sort == "rating_desc":
                items.sort(key=lambda h: (-h["rating"], str(h["hotel_id"])))
            elif params.sort == "name":
                items.sort(key=lambda h: (h["name"], str(h["hotel_id"])))
            else:
                sign = -1 if params.sort == "price_desc" else 1
                items.sort(key=lambda h: (sign * h["min_price"], str(h["hotel_id"])))
            start = (params.page - 1) * params.limit
            return {
                "items": items[start : start + params.limit],
                "total": len(items),
                "page": params.page,
                "limit": params.limit,
            }

    async def _room(self, uow, room, params):
        rates = await uow.rates.all(room_id=room.id, is_active=True)
        available = None
        if params.check_in:
            intervals = await uow.bookings.intervals([room.id], params.check_in, params.check_out)
            available = free_stock(room.stock, params.check_in, params.check_out, intervals)
        return {
            **public(room),
            "rates": [public(rate) for rate in rates],
            "photos": [public(p) for p in await uow.photos.all(room_id=room.id)],
            "available_count": available,
            "can_book": bool(rates)
            and (available is None or available >= params.rooms_count)
            and room.capacity * params.rooms_count >= params.guests_count,
        }

    async def hotel(self, hotel_id, params):
        self.validate_dates(params.check_in, params.check_out)
        async with self.uow_factory() as uow:
            hotel = await uow.hotels.get(hotel_id)
            if not hotel or not hotel.is_active:
                raise NotFoundError("Hotel not found")
            rooms = [
                await self._room(uow, room, params)
                for room in await uow.rooms.all(hotel_id=hotel_id, is_active=True)
            ]
            return {
                **public(hotel),
                "rooms": rooms,
                "photos": [public(p) for p in await uow.photos.all(hotel_id=hotel_id)],
                "reviews": [public(r) for r in await uow.reviews.all(hotel_id=hotel_id)],
            }

    async def room(self, room_id, params):
        self.validate_dates(params.check_in, params.check_out)
        async with self.uow_factory() as uow:
            room = await uow.rooms.get(room_id)
            hotel = await uow.hotels.get(room.hotel_id) if room else None
            if not room or not room.is_active or not hotel or not hotel.is_active:
                raise NotFoundError("Room not found")
            return await self._room(uow, room, params)

    async def create_hotel(self, data):
        async with self.uow_factory() as uow:
            hotel = await uow.hotels.add(**data.model_dump())
            await uow.commit()
            return public(hotel)

    async def update_hotel(self, hotel_id, data):
        async with self.uow_factory() as uow:
            hotel = await uow.hotels.get(hotel_id, lock=True)
            if not hotel:
                raise NotFoundError("Hotel not found")
            self.patch(hotel, data, nullable=("latitude", "longitude"))
            await uow.commit()
            return public(hotel)

    async def create_room(self, hotel_id, data):
        async with self.uow_factory() as uow:
            hotel = await uow.hotels.get(hotel_id, lock=True)
            if not hotel or not hotel.is_active:
                raise NotFoundError("Hotel not found")
            await self._validate_codes(uow, data.interior_styles, data.booking_purposes)
            room = await uow.rooms.add(hotel_id=hotel_id, **data.model_dump())
            await uow.commit()
            return public(room)

    async def update_room(self, room_id, data):
        async with self.uow_factory() as uow:
            room = await uow.rooms.get(room_id, lock=True)
            if not room:
                raise NotFoundError("Room not found")
            await self._validate_codes(uow, data.interior_styles or [], data.booking_purposes or [])
            if data.stock is not None and data.stock < room.stock:
                if await uow.bookings.intervals([room_id], self.today(), date(9999, 12, 31)):
                    raise ConflictError("Cannot reduce stock while future bookings exist")
            self.patch(room, data)
            await uow.commit()
            return public(room)

    async def create_rate(self, room_id, data):
        async with self.uow_factory() as uow:
            room = await uow.rooms.get(room_id, lock=True)
            if not room or not room.is_active:
                raise NotFoundError("Room not found")
            rate = await uow.rates.add(room_id=room_id, **data.model_dump())
            await uow.commit()
            return public(rate)

    async def update_rate(self, rate_id, data):
        async with self.uow_factory() as uow:
            rate = await uow.rates.get(rate_id)
            if not rate:
                raise NotFoundError("Rate not found")
            await uow.rooms.get(rate.room_id, lock=True)
            self.patch(rate, data)
            await uow.commit()
            return public(rate)

    async def add_photo(self, owner_id, data, kind):
        async with self.uow_factory() as uow:
            repo = uow.hotels if kind == "hotel" else uow.rooms
            if not await repo.get(owner_id):
                raise NotFoundError()
            photo = await uow.photos.add(
                **{f"{kind}_id": owner_id}, url=str(data.url), sort_order=data.sort_order
            )
            await uow.commit()
            return public(photo)


class FavoriteService(BaseService):
    async def add(self, user_id, hotel_id):
        async with self.uow_factory() as uow:
            await self.active_user(uow, user_id)
            hotel = await uow.hotels.get(hotel_id)
            if not hotel or not hotel.is_active:
                raise NotFoundError("Hotel not found")
            favorite = await uow.favorites.find(user_id, hotel_id)
            if favorite is None:
                favorite = await uow.favorites.add(user_id=user_id, hotel_id=hotel_id)
            await uow.commit()
            return public(favorite)

    async def list(self, user_id):
        async with self.uow_factory() as uow:
            items = []
            for favorite in await uow.favorites.all(user_id=user_id):
                hotel = await uow.hotels.get(favorite.hotel_id)
                items.append({**public(favorite), "hotel": public(hotel)})
            return {"items": items}

    async def get(self, user_id, favorite_id):
        async with self.uow_factory() as uow:
            return public(own(await uow.favorites.get(favorite_id), user_id))

    async def remove(self, user_id, favorite_id):
        async with self.uow_factory() as uow:
            await uow.favorites.remove(own(await uow.favorites.get(favorite_id), user_id))
            await uow.commit()


class ReviewService(BaseService):
    async def add(self, user_id, hotel_id, data):
        async with self.uow_factory() as uow:
            booking = own(await uow.bookings.get(data.booking_id), user_id)
            if (
                booking.hotel_id != hotel_id
                or booking.status != "confirmed"
                or booking.check_out > self.today()
            ):
                raise ValidationError("A review requires a completed stay at this hotel")
            # Serialize duplicate reviews and rating updates for the same hotel.
            hotel = await uow.hotels.get(hotel_id, lock=True)
            existing = await uow.reviews.all(booking_id=booking.id)
            if existing:
                raise ConflictError("This booking already has a review")
            review = await uow.reviews.add(user_id=user_id, hotel_id=hotel_id, **data.model_dump())
            hotel.rating = Decimal(str(await uow.reviews.hotel_rating(hotel_id))).quantize(
                Decimal("0.1")
            )
            await uow.commit()
            return public(review)
