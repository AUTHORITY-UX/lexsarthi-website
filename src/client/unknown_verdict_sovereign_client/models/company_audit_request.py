from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.company_audit_request_documents import CompanyAuditRequestDocuments


T = TypeVar("T", bound="CompanyAuditRequest")


@_attrs_define
class CompanyAuditRequest:
    """
    Attributes:
        company_name (str):
        industry (None | str | Unset):
        jurisdiction (str | Unset):  Default: 'india'.
        documents (CompanyAuditRequestDocuments | Unset):
        email (None | str | Unset):
        generate_pdf (bool | Unset):  Default: False.
    """

    company_name: str
    industry: None | str | Unset = UNSET
    jurisdiction: str | Unset = "india"
    documents: CompanyAuditRequestDocuments | Unset = UNSET
    email: None | str | Unset = UNSET
    generate_pdf: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        company_name = self.company_name

        industry: None | str | Unset
        if isinstance(self.industry, Unset):
            industry = UNSET
        else:
            industry = self.industry

        jurisdiction = self.jurisdiction

        documents: dict[str, Any] | Unset = UNSET
        if not isinstance(self.documents, Unset):
            documents = self.documents.to_dict()

        email: None | str | Unset
        if isinstance(self.email, Unset):
            email = UNSET
        else:
            email = self.email

        generate_pdf = self.generate_pdf

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "company_name": company_name,
            }
        )
        if industry is not UNSET:
            field_dict["industry"] = industry
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if documents is not UNSET:
            field_dict["documents"] = documents
        if email is not UNSET:
            field_dict["email"] = email
        if generate_pdf is not UNSET:
            field_dict["generate_pdf"] = generate_pdf

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.company_audit_request_documents import CompanyAuditRequestDocuments  # noqa: PLC0415

        d = dict(src_dict)
        company_name = d.pop("company_name")

        def _parse_industry(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        industry = _parse_industry(d.pop("industry", UNSET))

        jurisdiction = d.pop("jurisdiction", UNSET)

        _documents = d.pop("documents", UNSET)
        documents: CompanyAuditRequestDocuments | Unset
        if isinstance(_documents, Unset):
            documents = UNSET
        else:
            documents = CompanyAuditRequestDocuments.from_dict(_documents)

        def _parse_email(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        email = _parse_email(d.pop("email", UNSET))

        generate_pdf = d.pop("generate_pdf", UNSET)

        company_audit_request = cls(
            company_name=company_name,
            industry=industry,
            jurisdiction=jurisdiction,
            documents=documents,
            email=email,
            generate_pdf=generate_pdf,
        )

        company_audit_request.additional_properties = d
        return company_audit_request

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
