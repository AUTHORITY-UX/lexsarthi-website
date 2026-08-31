from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="EvolutionProposalRequest")


@_attrs_define
class EvolutionProposalRequest:
    """
    Attributes:
        title (str):
        description (str):
        category (str | Unset):  Default: 'feature'.
        priority (str | Unset):  Default: 'medium'.
        implementation_details (None | str | Unset):
    """

    title: str
    description: str
    category: str | Unset = "feature"
    priority: str | Unset = "medium"
    implementation_details: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        description = self.description

        category = self.category

        priority = self.priority

        implementation_details: None | str | Unset
        if isinstance(self.implementation_details, Unset):
            implementation_details = UNSET
        else:
            implementation_details = self.implementation_details

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "description": description,
            }
        )
        if category is not UNSET:
            field_dict["category"] = category
        if priority is not UNSET:
            field_dict["priority"] = priority
        if implementation_details is not UNSET:
            field_dict["implementation_details"] = implementation_details

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title = d.pop("title")

        description = d.pop("description")

        category = d.pop("category", UNSET)

        priority = d.pop("priority", UNSET)

        def _parse_implementation_details(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        implementation_details = _parse_implementation_details(d.pop("implementation_details", UNSET))

        evolution_proposal_request = cls(
            title=title,
            description=description,
            category=category,
            priority=priority,
            implementation_details=implementation_details,
        )

        evolution_proposal_request.additional_properties = d
        return evolution_proposal_request

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
