from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ComplianceCheck")


@_attrs_define
class ComplianceCheck:
    """
    Attributes:
        document (str):
        regulation (str | Unset):  Default: 'dpdpa'.
        jurisdiction (str | Unset):  Default: 'US'.
    """

    document: str
    regulation: str | Unset = "dpdpa"
    jurisdiction: str | Unset = "US"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        document = self.document

        regulation = self.regulation

        jurisdiction = self.jurisdiction

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "document": document,
            }
        )
        if regulation is not UNSET:
            field_dict["regulation"] = regulation
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        document = d.pop("document")

        regulation = d.pop("regulation", UNSET)

        jurisdiction = d.pop("jurisdiction", UNSET)

        compliance_check = cls(
            document=document,
            regulation=regulation,
            jurisdiction=jurisdiction,
        )

        compliance_check.additional_properties = d
        return compliance_check

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
