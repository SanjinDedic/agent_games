"""Unit tests for GoogleSheetsSchoolsProvider + URL helper."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.schools.providers import (
    GoogleSheetsSchoolsProvider,
    SchoolsProviderError,
    to_csv_export_url,
)


def testto_csv_export_url_with_gid():
    url = "https://docs.google.com/spreadsheets/d/abc_ID-123/edit#gid=456"
    assert to_csv_export_url(url) == (
        "https://docs.google.com/spreadsheets/d/abc_ID-123/export?format=csv&gid=456"
    )


def testto_csv_export_url_without_gid_defaults_to_zero():
    url = "https://docs.google.com/spreadsheets/d/abc_ID-123/edit"
    assert to_csv_export_url(url).endswith("gid=0")


def testto_csv_export_url_rejects_non_sheets_url():
    with pytest.raises(SchoolsProviderError):
        to_csv_export_url("https://example.com/spreadsheets/not-here")


def _ok(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = 200
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


def test_list_schools_happy_path():
    csv_text = "School\nWilletton SHS\nPerth Modern\n"
    provider = GoogleSheetsSchoolsProvider(
        "https://docs.google.com/spreadsheets/d/abc/edit"
    )
    with patch("backend.schools.providers.httpx.get", return_value=_ok(csv_text)) as g:
        assert provider.list_schools() == ["Willetton SHS", "Perth Modern"]
    assert g.call_count == 1


def test_list_schools_empty_sheet_returns_empty_list():
    provider = GoogleSheetsSchoolsProvider(
        "https://docs.google.com/spreadsheets/d/abc/edit"
    )
    with patch("backend.schools.providers.httpx.get", return_value=_ok("School\n")):
        assert provider.list_schools() == []


def test_list_schools_network_error_raises():
    provider = GoogleSheetsSchoolsProvider(
        "https://docs.google.com/spreadsheets/d/abc/edit"
    )
    with patch(
        "backend.schools.providers.httpx.get",
        side_effect=httpx.ConnectError("net"),
    ):
        with pytest.raises(SchoolsProviderError):
            provider.list_schools()


def test_list_schools_ignores_blank_rows_and_trims():
    csv_text = "School\n  Alpha  \n\nBeta\n \n"
    provider = GoogleSheetsSchoolsProvider(
        "https://docs.google.com/spreadsheets/d/abc/edit"
    )
    with patch("backend.schools.providers.httpx.get", return_value=_ok(csv_text)):
        assert provider.list_schools() == ["Alpha", "Beta"]
