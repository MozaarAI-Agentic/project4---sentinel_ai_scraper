"""Modèle SQLAlchemy pour la table `jobs`.

Ce modèle est volontairement séparé de l'entité de domaine `Job` (voir
api_gateway.domain.job). Le domaine reste un objet Python pur, testable
sans base de données ; ce module traduit sa forme persistée. Le mapping
JSON pour `result` et `failure_reason` correspond au champ JSONB défini en
Phase 5 (Database Design) - ici représenté en JSON générique pour rester
compatible avec le substitut de test SQLite (voir ADR-0008).
"""

from sqlalchemy import JSON, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JobModel(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        # Index composite défini en Phase 5 : "statut des jobs pour ce domaine"
        # est la requête la plus fréquente du système (dashboard, monitoring).
        Index("ix_jobs_domain_status", "domain", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    required_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)
