"""User persistence repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserModel
from app.db.repositories.base_repo import BaseRepository


class UsersRepository(BaseRepository[UserModel]):
    model_class = UserModel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_email(self, email: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.email == email)
        return self._session.scalars(stmt).first()

    def get_by_id(self, user_id: str) -> UserModel | None:
        return self._session.get(UserModel, user_id)

    def create(self, *, email: str, hashed_password: str, role: str = "user") -> UserModel:
        user = UserModel(email=email, hashed_password=hashed_password, role=role)
        return self.add(user)
