from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ContractAnalysis")


@_attrs_define
class ContractAnalysis:
    """
    Attributes:
        document (str):
        contract_type (str | Unset):  Default: 'general'.
        jurisdiction (str | Unset):  Default: 'US'.
        analyze_risks (bool | Unset):  Default: True.
    """

    document: str
    contract_type: str | Unset = "general"
    jurisdiction: str | Unset = "US"
    analyze_risks: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        document = self.document

        contract_type = self.contract_type

        jurisdiction = self.jurisdiction

        analyze_risks = self.analyze_risks

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "document": document,
            }
        )
        if contract_type is not UNSET:
            field_dict["contract_type"] = contract_type
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if analyze_risks is not UNSET:
            field_dict["analyze_risks"] = analyze_risks

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        document = d.pop("document")

        contract_type = d.pop("contract_type", UNSET)

        jurisdiction = d.pop("jurisdiction", UNSET)

        analyze_risks = d.pop("analyze_risks", UNSET)

        contract_analysis = cls(
            document=document,
            contract_type=contract_type,
            jurisdiction=jurisdiction,
            analyze_risks=analyze_risks,
        )

        contract_analysis.additional_properties = d
        return contract_analysis

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
