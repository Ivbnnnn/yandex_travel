from decimal import Decimal


async def seed_data(uow_factory, settings, passwords):
    async with uow_factory() as uow:
        # A database-level advisory lock serializes first startup of multiple processes.
        from sqlalchemy import text

        await uow.session.execute(text("SELECT pg_advisory_xact_lock(7042601)"))
        if not await uow.users.by_email(settings.ADMIN_EMAIL):
            await uow.users.add(
                email=settings.ADMIN_EMAIL.lower(),
                name="Administrator",
                role="admin",
                password_hash=await passwords.hash(settings.ADMIN_PASSWORD),
            )
        if not await uow.filters.all():
            for kind, values in (
                (
                    "interior_style",
                    [("light", "Светлый"), ("minimalism", "Минимализм"), ("loft", "Лофт")],
                ),
                (
                    "booking_purpose",
                    [
                        ("leisure", "Отдых"),
                        ("photoshoot", "Фотосессия"),
                        ("birthday", "День рождения"),
                    ],
                ),
            ):
                for code, name in values:
                    await uow.filters.add(kind=kind, code=code, name=name)
        if settings.SEED_DATA and not await uow.hotels.all():
            for city, coords in [
                ("Москва", ("55.755826", "37.617300")),
                ("Санкт-Петербург", ("59.934280", "30.335099")),
                ("Казань", ("55.796127", "49.106414")),
            ]:
                for index, title in enumerate(["У парка", "Тихий двор", "Городские истории"]):
                    hotel = await uow.hotels.add(
                        name=f"{title} · {city}",
                        city=city,
                        address=f"{city}, Центральная улица, {10 + index}",
                        description="Демонстрационный отель. Уютные номера, прогулки по городу и спокойный отдых.",
                        latitude=Decimal(coords[0]),
                        longitude=Decimal(coords[1]),
                        tags=["wifi", "parking"] if index % 2 == 0 else ["wifi", "pets"],
                    )
                    for style, name, capacity, stock, price, purposes in [
                        ("light", "Светлый стандарт", 2, 4, 4500, ["leisure", "photoshoot"]),
                        ("minimalism", "Минимализм", 2, 3, 3900, ["leisure"]),
                        ("loft", "Лофт", 4, 2, 6500, ["leisure", "photoshoot", "birthday"]),
                    ]:
                        room = await uow.rooms.add(
                            hotel_id=hotel.id,
                            name=name,
                            capacity=capacity,
                            stock=stock,
                            description="Категория одинаковых номеров. В наличии несколько экземпляров.",
                            price=Decimal(price + index * 500),
                            tags=["wifi", "desk"],
                            interior_styles=[style],
                            booking_purposes=purposes,
                        )
                        for breakfast in (False, True):
                            await uow.rates.add(
                                room_id=room.id,
                                name="С завтраком" if breakfast else "Без завтрака",
                                price=room.price + (Decimal("800") if breakfast else Decimal("0")),
                                breakfast_included=breakfast,
                                cancellation_policy="Бесплатная отмена до дня заезда",
                                conditions={"free_cancellation_before_check_in": True},
                            )
        await uow.commit()
