"""冷链订单边界规则测试。"""
from __future__ import annotations

import unittest

from app.services import order as order_service
from app.services.order import MODULE, OrderService


class FakeStore:
    def __init__(self, rows: list[dict]) -> None:
        self.tables = {MODULE: rows}

    def rows(self, module: str) -> list[dict]:
        return self.tables.setdefault(module, [])


class OrderServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_store = order_service.store
        self.rows = [
            {
                "id": 1,
                "订单编号": "ORD-001",
                "客户名称": "甲客户",
                "货物名称": "冻品",
                "status": "待受理",
            }
        ]
        order_service.store = FakeStore(self.rows)  # type: ignore[assignment]
        self.service = OrderService()

    def tearDown(self) -> None:
        order_service.store = self.original_store

    def test_exact_duplicate_submission_returns_existing_order(self) -> None:
        payload = {"订单编号": " ORD-001 ", "客户名称": "甲客户", "货物名称": "冻品"}

        first, _ = self.service.submit_entry(payload)
        second, message = self.service.submit_entry(payload)

        self.assertIs(first, self.rows[0])
        self.assertIs(second, self.rows[0])
        self.assertEqual(len(self.rows), 1)
        self.assertIn("未重复创建", message)

    def test_same_order_number_with_different_payload_is_rejected(self) -> None:
        entry, message = self.service.submit_entry(
            {"订单编号": "ORD-001", "客户名称": "乙客户", "货物名称": "冻品"}
        )

        self.assertIsNone(entry)
        self.assertEqual(len(self.rows), 1)
        self.assertIn("已存在", message)

    def test_unknown_order_number_returns_empty_items_and_zero_total(self) -> None:
        items, total = self.service.list_entries(keyword="NOT-EXISTS", page=1, size=20)

        self.assertEqual(items, [])
        self.assertEqual(total, 0)

    def test_customer_and_goods_filters_share_same_total_basis(self) -> None:
        self.rows.append(
            {"id": 2, "订单编号": "ORD-002", "客户名称": "乙客户", "货物名称": "蔬果", "status": "待受理"}
        )

        items, total = self.service.list_entries(customer="乙", goods="蔬", page=1, size=20)

        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], 2)


if __name__ == "__main__":
    unittest.main()
