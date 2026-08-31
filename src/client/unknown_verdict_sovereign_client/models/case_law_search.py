from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CaseLawSearch")


@_attrs_define
class CaseLawSearch:
    """
    Attributes:
        query (str):
        jurisdiction (str | Unset):  Default: 'US'.
        court (None | str | Unset):
        year_from (int | None | Unset):
        year_to (int | None | Unset):
    """

    query: str
    jurisdiction: str | Unset = "US"
    court: None | str | Unset = UNSET
    year_from: int | None | Unset = UNSET
    year_to: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        jurisdiction = self.jurisdiction

        court: None | str | Unset
        if isinstance(self.court, Unset):
            court = UNSET
        else:
            court = self.court

        year_from: int | None | Unset
        if isinstance(self.year_from, Unset):
            year_from = UNSET
        else:
            year_from = self.year_from

        year_to: int | None | Unset
        if isinstance(self.year_to, Unset):
            year_to = UNSET
        else:
            year_to = self.year_to

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if court is not UNSET:
            field_dict["court"] = court
        if year_from is not UNSET:
            field_dict["year_from"] = year_from
        if year_to is not UNSET:
            field_dict["year_to"] = year_to

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        jurisdiction = d.pop("jurisdiction", UNSET)

        def _parse_court(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        court = _parse_court(d.pop("court", UNSET))

        def _parse_year_from(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        year_from = _parse_year_from(d.pop("year_from", UNSET))

        def _parse_year_to(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        year_to = _parse_year_to(d.pop("year_to", UNSET))

        case_law_search = cls(
            query=query,
            jurisdiction=jurisdiction,
            court=court,
            year_from=year_from,
            year_to=year_to,
        )

        case_law_search.additional_properties = d
        return case_law_search

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
