from uuid import UUID

from sqlalchemy.orm import Session

from app.models.models import User, Project, UserProject


class UserRepository:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        return db.query(User).order_by(User.created_at).offset(skip).limit(limit).all()

    def get_count(self, db: Session) -> int:
        return db.query(User).count()

    def get_by_id(self, db: Session, user_id: UUID) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, db: Session, username: str) -> User | None:
        return db.query(User).filter(User.username == username.strip().lower()).first()

    def create(
        self,
        db: Session,
        *,
        username: str,
        full_name: str,
        password_hash: str,
        role: str,
        status: str = "active",
    ) -> User:
        db_user = User(
            username=username.strip().lower(),
            full_name=full_name.strip(),
            password_hash=password_hash,
            role=role,
            status=status,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def update(self, db: Session, user_id: UUID, fields: dict) -> User | None:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
        return db_user


class ProjectRepository:
    def get_all(self, db: Session) -> list[Project]:
        return db.query(Project).order_by(Project.name).all()

    def get_count(self, db: Session) -> int:
        return db.query(Project).count()

    def get_by_id(self, db: Session, project_id: UUID) -> Project | None:
        return db.query(Project).filter(Project.id == project_id).first()

    def get_by_name(self, db: Session, name: str) -> Project | None:
        return db.query(Project).filter(Project.name == name.strip()).first()

    def create(self, db: Session, name: str, description: str | None = None) -> Project:
        db_project = Project(name=name.strip(), description=description)
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project

    def projects_for_user(self, db: Session, user_id: UUID) -> list[Project]:
        return (
            db.query(Project)
            .join(UserProject, UserProject.project_id == Project.id)
            .filter(UserProject.user_id == user_id)
            .order_by(Project.name)
            .all()
        )

    def users_for_project(self, db: Session, project_id: UUID) -> list[User]:
        return (
            db.query(User)
            .join(UserProject, UserProject.user_id == User.id)
            .filter(UserProject.project_id == project_id)
            .order_by(User.username)
            .all()
        )

    def add_member(self, db: Session, project_id: UUID, user_id: UUID) -> UserProject | None:
        project = self.get_by_id(db, project_id)
        if not project:
            return None
        existing = (
            db.query(UserProject)
            .filter(
                UserProject.project_id == project_id,
                UserProject.user_id == user_id,
            )
            .first()
        )
        if existing:
            return existing
        membership = UserProject(project_id=project_id, user_id=user_id)
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return membership

    def remove_member(self, db: Session, project_id: UUID, user_id: UUID) -> bool:
        membership = (
            db.query(UserProject)
            .filter(
                UserProject.project_id == project_id,
                UserProject.user_id == user_id,
            )
            .first()
        )
        if not membership:
            return False
        db.delete(membership)
        db.commit()
        return True


user_repo = UserRepository()
project_repo = ProjectRepository()