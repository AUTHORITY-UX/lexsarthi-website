from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="MultiJurisdictionRequest")


@_attrs_define
class MultiJurisdictionRequest:
    """
    Attributes:
        query (str):
        jurisdiction (str | Unset):  Default: 'india'.
        model (None | str | Unset):
        compare_with (list[str] | Unset):
    """

    query: str
    jurisdiction: str | Unset = "india"
    model: None | str | Unset = UNSET
    compare_with: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        jurisdiction = self.jurisdiction

        model: None | str | Unset
        if isinstance(self.model, Unset):
            model = UNSET
        else:
            model = self.model

        compare_with: list[str] | Unset = UNSET
        if not isinstance(self.compare_with, Unset):
            compare_with = self.compare_with

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if model is not UNSET:
            field_dict["model"] = model
        if compare_with is not UNSET:
            field_dict["compare_with"] = compare_with

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        jurisdiction = d.pop("jurisdiction", UNSET)

        def _parse_model(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        model = _parse_model(d.pop("model", UNSET))

        compare_with = cast(list[str], d.pop("compare_with", UNSET))

        multi_jurisdiction_request = cls(
            query=query,
            jurisdiction=jurisdiction,
            model=model,
            compare_with=compare_with,
        )

        multi_jurisdiction_request.additional_properties = d
        return multi_jurisdiction_request

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
