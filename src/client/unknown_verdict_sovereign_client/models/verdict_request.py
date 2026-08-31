from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="VerdictRequest")


@_attrs_define
class VerdictRequest:
    """
    Attributes:
        query (str):
        mode (None | str | Unset):
        model (None | str | Unset):
        jurisdiction (str | Unset):  Default: 'india'.
        include_dissent (bool | Unset):  Default: False.
    """

    query: str
    mode: None | str | Unset = UNSET
    model: None | str | Unset = UNSET
    jurisdiction: str | Unset = "india"
    include_dissent: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        mode: None | str | Unset
        if isinstance(self.mode, Unset):
            mode = UNSET
        else:
            mode = self.mode

        model: None | str | Unset
        if isinstance(self.model, Unset):
            model = UNSET
        else:
            model = self.model

        jurisdiction = self.jurisdiction

        include_dissent = self.include_dissent

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if mode is not UNSET:
            field_dict["mode"] = mode
        if model is not UNSET:
            field_dict["model"] = model
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if include_dissent is not UNSET:
            field_dict["include_dissent"] = include_dissent

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        def _parse_mode(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        mode = _parse_mode(d.pop("mode", UNSET))

        def _parse_model(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        model = _parse_model(d.pop("model", UNSET))

        jurisdiction = d.pop("jurisdiction", UNSET)

        include_dissent = d.pop("include_dissent", UNSET)

        verdict_request = cls(
            query=query,
            mode=mode,
            model=model,
            jurisdiction=jurisdiction,
            include_dissent=include_dissent,
        )

        verdict_request.additional_properties = d
        return verdict_request

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
