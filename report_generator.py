"""Generate inventory reports from DummyJSON API responses."""

from math import isfinite
from typing import Any


class InventoryReportGenerator:
    """Analyze product data returned by :class:`InventoryAPIClient`.

    Accepts a product-list response (``{"products": [...]}``), a list of
    products, or one product response. Aggregate metrics describe only the
    products present in the supplied data; paginated API responses may contain
    just a subset of the full inventory.
    """

    def __init__(self, raw_data: dict[str, Any] | list[dict[str, Any]]) -> None:
        if isinstance(raw_data, list):
            products = raw_data
            self.reported_total: int | None = None
        elif isinstance(raw_data, dict) and "products" in raw_data:
            products = raw_data["products"]
            self.reported_total = raw_data.get("total")
            if self.reported_total is not None and (
                isinstance(self.reported_total, bool)
                or not isinstance(self.reported_total, int)
                or self.reported_total < 0
            ):
                raise ValueError("'total' must be a non-negative integer")
        elif isinstance(raw_data, dict):
            products = [raw_data]
            self.reported_total = None
        else:
            raise TypeError("raw_data must be a product list or API response object")

        if not isinstance(products, list):
            raise ValueError("API response field 'products' must be a list")

        self.products = tuple(
            self._validate_product(product, index)
            for index, product in enumerate(products)
        )

    def generate_summary(self) -> dict[str, int | float | None]:
        """Return aggregate inventory metrics for the supplied products."""
        product_count = len(self.products)
        total_stock = sum(product["stock"] for product in self.products)
        inventory_value = sum(
            product["price"] * product["stock"] for product in self.products
        )
        average_price = (
            sum(product["price"] for product in self.products) / product_count
            if product_count
            else 0.0
        )

        return {
            "products_in_response": product_count,
            "reported_total_products": self.reported_total,
            "total_stock_units": total_stock,
            "inventory_value": round(inventory_value, 2),
            "average_price": round(average_price, 2),
            "out_of_stock_products": sum(
                product["stock"] == 0 for product in self.products
            ),
            "category_count": len({product["category"] for product in self.products}),
        }

    def generate_category_report(self) -> dict[str, dict[str, int | float]]:
        """Return product count, stock, and value grouped by category."""
        report: dict[str, dict[str, int | float]] = {}
        for product in self.products:
            category = product["category"]
            metrics = report.setdefault(
                category,
                {"product_count": 0, "stock_units": 0, "inventory_value": 0.0},
            )
            metrics["product_count"] += 1
            metrics["stock_units"] += product["stock"]
            metrics["inventory_value"] += product["price"] * product["stock"]

        for metrics in report.values():
            metrics["inventory_value"] = round(metrics["inventory_value"], 2)
        return report

    def get_low_stock_products(
        self, *, threshold: int = 10
    ) -> list[dict[str, Any]]:
        """Return products with stock at or below ``threshold``."""
        if isinstance(threshold, bool) or not isinstance(threshold, int):
            raise TypeError("threshold must be an integer")
        if threshold < 0:
            raise ValueError("threshold must be zero or greater")

        return [
            dict(product)
            for product in self.products
            if product["stock"] <= threshold
        ]

    def generate_report(self, *, low_stock_threshold: int = 10) -> dict[str, Any]:
        """Return a combined summary, category breakdown, and low-stock list."""
        return {
            "summary": self.generate_summary(),
            "by_category": self.generate_category_report(),
            "low_stock_products": self.get_low_stock_products(
                threshold=low_stock_threshold
            ),
        }

    @staticmethod
    def _validate_product(product: Any, index: int) -> dict[str, Any]:
        if not isinstance(product, dict):
            raise ValueError(f"product at index {index} must be an object")

        for field in ("id", "title", "category", "price", "stock"):
            if field not in product:
                raise ValueError(f"product at index {index} is missing '{field}'")

        if isinstance(product["id"], bool) or not isinstance(product["id"], int):
            raise ValueError(f"product at index {index} has an invalid 'id'")
        for field in ("title", "category"):
            if not isinstance(product[field], str) or not product[field].strip():
                raise ValueError(
                    f"product at index {index} has an invalid '{field}'"
                )
        for field in ("price", "stock"):
            value = product[field]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    f"product at index {index} has an invalid '{field}'"
                )

        return dict(product)
