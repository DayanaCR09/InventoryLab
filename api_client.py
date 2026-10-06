"""Client for the public DummyJSON products API."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class DummyJSONAPIError(RuntimeError):
    """Raised when a DummyJSON request fails or returns invalid JSON."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class InventoryAPIClient:
    """Read and simulate product changes through DummyJSON.

    DummyJSON simulates product creation, updates, and deletion; those changes
    are not persisted by the remote service.
    """

    def __init__(
        self,
        base_url: str = "https://dummyjson.com",
        timeout: float = 10.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def list_products(self, *, limit: int = 30, skip: int = 0) -> dict[str, Any]:
        """Return a page of products and pagination metadata."""
        self._validate_pagination(limit, skip)
        return self._request("products", params={"limit": limit, "skip": skip})

    def get_product(self, product_id: int) -> dict[str, Any]:
        """Return a product by its ID."""
        self._validate_product_id(product_id)
        return self._request(f"products/{product_id}")

    def search_products(
        self, query: str, *, limit: int = 30, skip: int = 0
    ) -> dict[str, Any]:
        """Search products by title, description, or other supported fields."""
        self._validate_pagination(limit, skip)
        return self._request(
            "products/search",
            params={"q": query, "limit": limit, "skip": skip},
        )

    def list_categories(self) -> list[dict[str, Any]]:
        """Return the available product categories."""
        return self._request("products/categories")

    def list_products_by_category(
        self, category: str, *, limit: int = 30, skip: int = 0
    ) -> dict[str, Any]:
        """Return a page of products in a category slug."""
        self._validate_pagination(limit, skip)
        category_slug = quote(category, safe="")
        return self._request(
            f"products/category/{category_slug}",
            params={"limit": limit, "skip": skip},
        )

    def add_product(self, product: dict[str, Any]) -> dict[str, Any]:
        """Simulate creating a product."""
        return self._request("products/add", method="POST", payload=product)

    def update_product(
        self, product_id: int, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Simulate updating a product."""
        self._validate_product_id(product_id)
        return self._request(
            f"products/{product_id}", method="PATCH", payload=updates
        )

    def delete_product(self, product_id: int) -> dict[str, Any]:
        """Simulate deleting a product."""
        self._validate_product_id(product_id)
        return self._request(f"products/{product_id}", method="DELETE")

    def _request(
        self,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
        except HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            raise DummyJSONAPIError(
                f"DummyJSON request failed with HTTP {error.code}: {error_body}",
                status_code=error.code,
            ) from error
        except URLError as error:
            raise DummyJSONAPIError(f"DummyJSON request failed: {error.reason}") from error

        try:
            return json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise DummyJSONAPIError(
                f"DummyJSON returned invalid JSON for {path}"
            ) from error

    @staticmethod
    def _validate_pagination(limit: int, skip: int) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if skip < 0:
            raise ValueError("skip must be zero or greater")

    @staticmethod
    def _validate_product_id(product_id: int) -> None:
        if product_id < 1:
            raise ValueError("product_id must be at least 1")
