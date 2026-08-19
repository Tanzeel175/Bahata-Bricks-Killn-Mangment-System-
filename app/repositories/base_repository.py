from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base generic repository providing standard CRUD operations."""

    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    def get_by_id(self, id_val) -> Optional[T]:
        return self.session.query(self.model_class).get(id_val)

    def get_all(self) -> List[T]:
        return self.session.query(self.model_class).all()

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: T) -> T:
        self.session.merge(entity)
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        self.session.delete(entity)
        self.session.flush()
