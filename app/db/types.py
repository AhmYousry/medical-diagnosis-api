from enum import StrEnum

from sqlalchemy import Enum


def pg_enum(enum_class: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=True,
        values_callable=lambda enum: [item.value for item in enum],
    )
