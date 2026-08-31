from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ChatResponse")


@_attrs_define
class ChatResponse:
    """
    Attributes:
        response (str):
        service (str):
        jurisdiction (str):
        agents_used (list[str]):
        model (str):
        timestamp (str):
    """

    response: str
    service: str
    jurisdiction: str
    agents_used: list[str]
    model: str
    timestamp: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        response = self.response

        service = self.service

        jurisdiction = self.jurisdiction

        agents_used = self.agents_used

        model = self.model

        timestamp = self.timestamp

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "response": response,
                "service": service,
                "jurisdiction": jurisdiction,
                "agents_used": agents_used,
                "model": model,
                "timestamp": timestamp,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        response = d.pop("response")

        service = d.pop("service")

        jurisdiction = d.pop("jurisdiction")

        agents_used = cast(list[str], d.pop("agents_used"))

        model = d.pop("model")

        timestamp = d.pop("timestamp")

        chat_response = cls(
            response=response,
            service=service,
            jurisdiction=jurisdiction,
            agents_used=agents_used,
            model=model,
            timestamp=timestamp,
        )

        chat_response.additional_properties = d
        return chat_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
