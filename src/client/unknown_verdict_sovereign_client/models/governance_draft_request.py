from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GovernanceDraftRequest")


@_attrs_define
class GovernanceDraftRequest:
    """
    Attributes:
        title (str):
        content (str):
        policy_type (str):
        stakeholders (list[str] | None | Unset):
    """

    title: str
    content: str
    policy_type: str
    stakeholders: list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        content = self.content

        policy_type = self.policy_type

        stakeholders: list[str] | None | Unset
        if isinstance(self.stakeholders, Unset):
            stakeholders = UNSET
        elif isinstance(self.stakeholders, list):
            stakeholders = self.stakeholders

        else:
            stakeholders = self.stakeholders

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "content": content,
                "policy_type": policy_type,
            }
        )
        if stakeholders is not UNSET:
            field_dict["stakeholders"] = stakeholders

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title = d.pop("title")

        content = d.pop("content")

        policy_type = d.pop("policy_type")

        def _parse_stakeholders(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                stakeholders_type_0 = cast(list[str], data)

                return stakeholders_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        stakeholders = _parse_stakeholders(d.pop("stakeholders", UNSET))

        governance_draft_request = cls(
            title=title,
            content=content,
            policy_type=policy_type,
            stakeholders=stakeholders,
        )

        governance_draft_request.additional_properties = d
        return governance_draft_request

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
