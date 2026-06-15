"""Modèle SQLAlchemy pour la table `selectors`.

Simplification assumée par rapport au schéma complet de la Phase 5 : le
champ `page_type` n'est pas repris ici, car l'entité de domaine `Selector`
(Cycle 2) ne le porte pas non plus - ce projet MVP traite un type de page
par domaine. Un site cible avec plusieurs types de page distincts (liste vs
détail produit) nécessiterait de réintroduire ce champ ; c'est documenté
comme limitation connue plutôt que silencieusement omis.
"""

from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SelectorModel(Base):
    __tablename__ = "selectors"
    __table_args__ = (
        # Une seule ligne active par (domain, field_name) à la fois - la
        # contrainte d'unicité complète (Phase 5) serait une contrainte SQL
        # partielle (WHERE is_active) ; SQLite ne la supporte pas nativement,
        # elle est donc appliquée au niveau applicatif dans le repository.
        Index("ix_selectors_domain_field", "domain", "field_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    selector_value: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
