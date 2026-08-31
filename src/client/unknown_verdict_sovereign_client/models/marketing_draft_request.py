from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="MarketingDraftRequest")


@_attrs_define
class MarketingDraftRequest:
    """
    Attributes:
        type_ (str):
        topic (None | str | Unset):
        tone (str | Unset):  Default: 'professional'.
        target_audience (None | str | Unset):
        call_to_action (None | str | Unset):
    """

    type_: str
    topic: None | str | Unset = UNSET
    tone: str | Unset = "professional"
    target_audience: None | str | Unset = UNSET
    call_to_action: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_

        topic: None | str | Unset
        if isinstance(self.topic, Unset):
            topic = UNSET
        else:
            topic = self.topic

        tone = self.tone

        target_audience: None | str | Unset
        if isinstance(self.target_audience, Unset):
            target_audience = UNSET
        else:
            target_audience = self.target_audience

        call_to_action: None | str | Unset
        if isinstance(self.call_to_action, Unset):
            call_to_action = UNSET
        else:
            call_to_action = self.call_to_action

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )
        if topic is not UNSET:
            field_dict["topic"] = topic
        if tone is not UNSET:
            field_dict["tone"] = tone
        if target_audience is not UNSET:
            field_dict["target_audience"] = target_audience
        if call_to_action is not UNSET:
            field_dict["call_to_action"] = call_to_action

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = d.pop("type")

        def _parse_topic(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        topic = _parse_topic(d.pop("topic", UNSET))

        tone = d.pop("tone", UNSET)

        def _parse_target_audience(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        target_audience = _parse_target_audience(d.pop("target_audience", UNSET))

        def _parse_call_to_action(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        call_to_action = _parse_call_to_action(d.pop("call_to_action", UNSET))

        marketing_draft_request = cls(
            type_=type_,
            topic=topic,
            tone=tone,
            target_audience=target_audience,
            call_to_action=call_to_action,
        )

        marketing_draft_request.additional_properties = d
        return marketing_draft_request

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
