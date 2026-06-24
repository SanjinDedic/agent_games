
import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Hint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    line_number: int = Field(ge=1)
    quoted_line: str
    assumptions: list[str]
    small_hint: str
    big_hint: str
    priority: int = Field(ge=1, le=5)
    bug: bool

test_hint = Hint(
    line_number=5,
    quoted_line="    total = 0",
    assumptions=["total persists between iterations"],
    small_hint="When does total get reset to zero?",
    big_hint="total = 0 sits inside the loop, so it resets every iteration. Move it above the loop.",
    priority=1,
    bug=True,
)


class Hint2(BaseModel):
    line_number: int = Field(ge=1)
    quoted_line: str
    assumptions: list[str]
    small_hint: str
    big_hint: str
    priority: int = Field(ge=1, le=5)
    bug: bool

test_hint2 = Hint2(
    line_number=5,
    quoted_line="    total = 0",
    assumptions=["total persists between iterations"],
    small_hint="When does total get reset to zero?",
    big_hint="total = 0 sits inside the loop, so it resets every iteration. Move it above the loop.",
    priority=1,
    bug=True,
)


print("OBJECT")
print(test_hint.model_dump_json(indent=2))


print("BLUEPRINT")
print(test_hint.model_json_schema())

print("BLUEPRINT WITHOUT extra='forbid'")
print(test_hint2.model_json_schema())