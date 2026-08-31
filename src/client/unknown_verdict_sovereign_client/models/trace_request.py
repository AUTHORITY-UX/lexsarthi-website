from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.trace_request_metadata_type_0 import TraceRequestMetadataType0


T = TypeVar("T", bound="TraceRequest")


@_attrs_define
class TraceRequest:
    """
    Attributes:
        query (str):
        service (str):
        response (str):
        agents (list[str]):
        metadata (None | TraceRequestMetadataType0 | Unset):
    """

    query: str
    service: str
    response: str
    agents: list[str]
    metadata: None | TraceRequestMetadataType0 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.trace_request_metadata_type_0 import TraceRequestMetadataType0  # noqa: PLC0415

        query = self.query

        service = self.service

        response = self.response

        agents = self.agents

        metadata: dict[str, Any] | None | Unset
        if isinstance(self.metadata, Unset):
            metadata = UNSET
        elif isinstance(self.metadata, TraceRequestMetadataType0):
            metadata = self.metadata.to_dict()
        else:
            metadata = self.metadata

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
                "service": service,
                "response": response,
                "agents": agents,
            }
        )
        if metadata is not UNSET:
            field_dict["metadata"] = metadata

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.trace_request_metadata_type_0 import TraceRequestMetadataType0  # noqa: PLC0415

        d = dict(src_dict)
        query = d.pop("query")

        service = d.pop("service")

        response = d.pop("response")

        agents = cast(list[str], d.pop("agents"))

        def _parse_metadata(data: object) -> None | TraceRequestMetadataType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                metadata_type_0 = TraceRequestMetadataType0.from_dict(data)

                return metadata_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | TraceRequestMetadataType0 | Unset, data)

        metadata = _parse_metadata(d.pop("metadata", UNSET))

        trace_request = cls(
            query=query,
            service=service,
            response=response,
            agents=agents,
            metadata=metadata,
        )

        trace_request.additional_properties = d
        return trace_request

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
