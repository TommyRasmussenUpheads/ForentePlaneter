from sqlalchemy import String, Boolean, Integer, SmallInteger, BigInteger, Float, ForeignKey, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class GameRound(Base):
    __tablename__ = "game_round"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="lobby")
    current_tick: Mapped[int] = mapped_column(Integer, default=0)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SolarSystem(Base):
    __tablename__ = "solar_systems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    hex_q: Mapped[int] = mapped_column(Integer, nullable=False)
    hex_r: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_npc: Mapped[bool] = mapped_column(Boolean, default=False)
    is_elder_race: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unknown_region: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    planets: Mapped[list["Planet"]] = relationship("Planet", back_populates="solar_system")


class SystemRoute(Base):
    __tablename__ = "system_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_system_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("solar_systems.id"), nullable=False)
    to_system_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("solar_systems.id"), nullable=False)
    travel_ticks: Mapped[int] = mapped_column(Integer, default=6)


class Planet(Base):
    __tablename__ = "planets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    solar_system_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("solar_systems.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    planet_type: Mapped[str] = mapped_column(String(16), nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    orbit_slot: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    travel_ticks: Mapped[int] = mapped_column(SmallInteger, default=0)
    blockade_status: Mapped[str] = mapped_column(String(16), default="none")

    metal: Mapped[int] = mapped_column(BigInteger, default=0)
    energy: Mapped[int] = mapped_column(BigInteger, default=0)
    gas: Mapped[int] = mapped_column(BigInteger, default=0)

    metal_production: Mapped[int] = mapped_column(Integer, default=0)
    energy_production: Mapped[int] = mapped_column(Integer, default=0)
    gas_production: Mapped[int] = mapped_column(Integer, default=0)

    score: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    solar_system: Mapped["SolarSystem"] = relationship("SolarSystem", back_populates="planets")
