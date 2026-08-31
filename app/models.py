from sqlalchemy import String, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Plugin(Base):

    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True
    )

    description: Mapped[str] = mapped_column(
        Text
    )

    path: Mapped[str] = mapped_column(
        String(500)
    )

    manifest: Mapped[dict] = mapped_column(
        JSON
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

class Task(Base):

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    plugin_id: Mapped[int] = mapped_column(
        ForeignKey("plugins.id")
    )

    parameters: Mapped[dict] = mapped_column(
        JSON
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="queued"
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )