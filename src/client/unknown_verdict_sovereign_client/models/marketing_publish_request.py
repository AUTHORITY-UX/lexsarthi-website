from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="MarketingPublishRequest")


@_attrs_define
class MarketingPublishRequest:
    """
    Attributes:
        draft_id (str):
        platform (str):
        schedule_at (None | str | Unset):
        human_approved (bool | Unset):  Default: False.
    """

    draft_id: str
    platform: str
    schedule_at: None | str | Unset = UNSET
    human_approved: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        draft_id = self.draft_id

        platform = self.platform

        schedule_at: None | str | Unset
        if isinstance(self.schedule_at, Unset):
            schedule_at = UNSET
        else:
            schedule_at = self.schedule_at

        human_approved = self.human_approved

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "draft_id": draft_id,
                "platform": platform,
            }
        )
        if schedule_at is not UNSET:
            field_dict["schedule_at"] = schedule_at
        if human_approved is not UNSET:
            field_dict["human_approved"] = human_approved

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        draft_id = d.pop("draft_id")

        platform = d.pop("platform")

        def _parse_schedule_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        schedule_at = _parse_schedule_at(d.pop("schedule_at", UNSET))

        human_approved = d.pop("human_approved", UNSET)

        marketing_publish_request = cls(
            draft_id=draft_id,
            platform=platform,
            schedule_at=schedule_at,
            human_approved=human_approved,
        )

        marketing_publish_request.additional_properties = d
        return marketing_publish_request

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
