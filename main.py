"""Fetch products and print an inventory report."""

import json
import sys
from typing import Any

from api_client import DummyJSONAPIError, InventoryAPIClient
from report_generator import InventoryReportGenerator


def main() -> int:
    """Fetch one product page, generate reports, and print them as JSON."""
    client = InventoryAPIClient()

    try:
        raw_data: dict[str, Any] = client.list_products()
    except DummyJSONAPIError as error:
        print(f"Unable to retrieve inventory: {error}", file=sys.stderr)
        return 1

    report_generator = InventoryReportGenerator(raw_data)
    report = report_generator.generate_report()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
