from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AgentEvolveRequest")


@_attrs_define
class AgentEvolveRequest:
    """
    Attributes:
        agent_id (str):
        evolution_type (str | Unset):  Default: 'skill'.
    """

    agent_id: str
    evolution_type: str | Unset = "skill"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        agent_id = self.agent_id

        evolution_type = self.evolution_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "agent_id": agent_id,
            }
        )
        if evolution_type is not UNSET:
            field_dict["evolution_type"] = evolution_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        agent_id = d.pop("agent_id")

        evolution_type = d.pop("evolution_type", UNSET)

        agent_evolve_request = cls(
            agent_id=agent_id,
            evolution_type=evolution_type,
        )

        agent_evolve_request.additional_properties = d
        return agent_evolve_request

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
