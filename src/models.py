import pydantic
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class BaseModel(pydantic.BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
    )


class Story(BaseModel):
    id: str
    title: str
    description: str
    priority: int
    acceptance_criteria: list[str]
    passes: bool


class CodexResultBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
