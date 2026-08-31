from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PrivacyScanRequest")


@_attrs_define
class PrivacyScanRequest:
    """
    Attributes:
        text (str):
        scan_type (str | Unset):  Default: 'compliance'.
        regulation (str | Unset):  Default: 'dpdpa'.
    """

    text: str
    scan_type: str | Unset = "compliance"
    regulation: str | Unset = "dpdpa"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        text = self.text

        scan_type = self.scan_type

        regulation = self.regulation

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "text": text,
            }
        )
        if scan_type is not UNSET:
            field_dict["scan_type"] = scan_type
        if regulation is not UNSET:
            field_dict["regulation"] = regulation

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        text = d.pop("text")

        scan_type = d.pop("scan_type", UNSET)

        regulation = d.pop("regulation", UNSET)

        privacy_scan_request = cls(
            text=text,
            scan_type=scan_type,
            regulation=regulation,
        )

        privacy_scan_request.additional_properties = d
        return privacy_scan_request

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
