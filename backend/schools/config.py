"""Typed configuration for SchoolsProvider sources.

The League.schools_config column stores a JSON dict tagged by ``source``;
this module gives that dict a Pydantic shape so reads and writes go through
one validated path.
"""

from typing import Annotated, List, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class StaticSchoolsConfig(BaseModel):
    source: Literal["static"] = "static"
    schools: List[str]


class GoogleSheetsSchoolsConfig(BaseModel):
    source: Literal["google_sheets"] = "google_sheets"
    sheet_url: str


SchoolsConfig = Annotated[
    Union[StaticSchoolsConfig, GoogleSheetsSchoolsConfig],
    Field(discriminator="source"),
]

_ADAPTER: TypeAdapter[SchoolsConfig] = TypeAdapter(SchoolsConfig)


def parse_schools_config(raw: dict) -> Union[StaticSchoolsConfig, GoogleSheetsSchoolsConfig]:
    """Validate and parse a raw schools_config dict into its typed model."""
    return _ADAPTER.validate_python(raw)
