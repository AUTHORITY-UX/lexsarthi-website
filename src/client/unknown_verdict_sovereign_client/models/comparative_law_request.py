from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ComparativeLawRequest")


@_attrs_define
class ComparativeLawRequest:
    """
    Attributes:
        query (str):
        jurisdictions (list[str] | Unset):
        model (None | str | Unset):
        focus_areas (list[str] | None | Unset):
    """

    query: str
    jurisdictions: list[str] | Unset = UNSET
    model: None | str | Unset = UNSET
    focus_areas: list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        jurisdictions: list[str] | Unset = UNSET
        if not isinstance(self.jurisdictions, Unset):
            jurisdictions = self.jurisdictions

        model: None | str | Unset
        if isinstance(self.model, Unset):
            model = UNSET
        else:
            model = self.model

        focus_areas: list[str] | None | Unset
        if isinstance(self.focus_areas, Unset):
            focus_areas = UNSET
        elif isinstance(self.focus_areas, list):
            focus_areas = self.focus_areas

        else:
            focus_areas = self.focus_areas

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if jurisdictions is not UNSET:
            field_dict["jurisdictions"] = jurisdictions
        if model is not UNSET:
            field_dict["model"] = model
        if focus_areas is not UNSET:
            field_dict["focus_areas"] = focus_areas

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        jurisdictions = cast(list[str], d.pop("jurisdictions", UNSET))

        def _parse_model(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        model = _parse_model(d.pop("model", UNSET))

        def _parse_focus_areas(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                focus_areas_type_0 = cast(list[str], data)

                return focus_areas_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        focus_areas = _parse_focus_areas(d.pop("focus_areas", UNSET))

        comparative_law_request = cls(
            query=query,
            jurisdictions=jurisdictions,
            model=model,
            focus_areas=focus_areas,
        )

        comparative_law_request.additional_properties = d
        return comparative_law_request

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
