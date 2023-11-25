from sqlalchemy import Boolean, ForeignKey, Integer, String, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(50), unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=True)
    avatar: Mapped[str] = mapped_column(String(255), nullable=True)
    refresh_token: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        "created_at", DateTime, default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        "updated_at", DateTime, default=func.now(), onupdate=func.now()
    )
    confirmed: Mapped[Boolean] = mapped_column(Boolean, default=False)
    contact: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="user", cascade="all,delete", passive_deletes=True,
        )


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(50), unique=True)
    phone: Mapped[str] = mapped_column(String(50), unique=True)
    birthday: Mapped[Date] = mapped_column(Date)
    created_at: Mapped[DateTime] = mapped_column(
        "created_at", DateTime, default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        "updated_at", DateTime, default=func.now(), onupdate=func.now()
    )
    user_id: Mapped[int] = mapped_column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship("User", back_populates="contact")
