from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="WebSearchRequest")


@_attrs_define
class WebSearchRequest:
    """
    Attributes:
        query (str):
        num_results (int | Unset):  Default: 10.
        region (str | Unset):  Default: 'us'.
        targeted (bool | Unset):  Default: False.
    """

    query: str
    num_results: int | Unset = 10
    region: str | Unset = "us"
    targeted: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        num_results = self.num_results

        region = self.region

        targeted = self.targeted

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if num_results is not UNSET:
            field_dict["num_results"] = num_results
        if region is not UNSET:
            field_dict["region"] = region
        if targeted is not UNSET:
            field_dict["targeted"] = targeted

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        num_results = d.pop("num_results", UNSET)

        region = d.pop("region", UNSET)

        targeted = d.pop("targeted", UNSET)

        web_search_request = cls(
            query=query,
            num_results=num_results,
            region=region,
            targeted=targeted,
        )

        web_search_request.additional_properties = d
        return web_search_request

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
