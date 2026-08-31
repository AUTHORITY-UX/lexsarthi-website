from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ReviewRequest")


@_attrs_define
class ReviewRequest:
    """
    Attributes:
        document (str):
        review_type (str | Unset):  Default: 'contract'.
        jurisdiction (str | Unset):  Default: 'US'.
        depth (str | Unset):  Default: 'standard'.
    """

    document: str
    review_type: str | Unset = "contract"
    jurisdiction: str | Unset = "US"
    depth: str | Unset = "standard"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        document = self.document

        review_type = self.review_type

        jurisdiction = self.jurisdiction

        depth = self.depth

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "document": document,
            }
        )
        if review_type is not UNSET:
            field_dict["review_type"] = review_type
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if depth is not UNSET:
            field_dict["depth"] = depth

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        document = d.pop("document")

        review_type = d.pop("review_type", UNSET)

        jurisdiction = d.pop("jurisdiction", UNSET)

        depth = d.pop("depth", UNSET)

        review_request = cls(
            document=document,
            review_type=review_type,
            jurisdiction=jurisdiction,
            depth=depth,
        )

        review_request.additional_properties = d
        return review_request

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
