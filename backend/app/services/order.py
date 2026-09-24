"""冷链订单业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from threading import Lock
from typing import Any

from app.store import store

MODULE = "order"
REQUIRED_FIELDS = ["订单编号", "客户名称", "货物名称"]
STATUS_ORDER = ["待受理", "已受理", "已调度", "已完结", "已取消"]
ACTION_RULES = {"受理订单": "已受理", "调度派车": "已调度", "取消订单": "已取消"}
NEGATIVE_ACTIONS = []

_CREATE_LOCK = Lock()


class OrderService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        customer: str | None = None,
        goods: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)

        keyword = (keyword or "").strip()
        customer = (customer or "").strip()
        goods = (goods or "").strip()
        status = (status or "").strip()
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("订单编号", ""))]
        if customer:
            rows = [row for row in rows if customer in str(row.get("客户名称", ""))]
        if goods:
            rows = [row for row in rows if goods in str(row.get("货物名称", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        """兼容旧调用的登记入口；重复编号等业务原因通过异常说明。"""
        entry, message = self.submit_entry(values)
        if entry is not None:
            return entry, []
        if message.startswith("缺少必填字段："):
            return None, message.removeprefix("缺少必填字段：").split("、")
        raise ValueError(message)

    def submit_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """登记订单，并在同一把锁内完成必填与订单编号唯一性校验。"""
        normalized = {
            field: str(values.get(field) or "").strip()
            for field in REQUIRED_FIELDS
        }
        missing = [field for field in REQUIRED_FIELDS if not normalized[field]]
        if missing:
            return None, f"缺少必填字段：{'、'.join(missing)}"

        with _CREATE_LOCK:
            rows = store.rows(MODULE)
            order_no = normalized["订单编号"]
            existing = next(
                (row for row in rows if str(row.get("订单编号", "")).strip() == order_no),
                None,
            )
            if existing is not None:
                same_payload = all(
                    str(existing.get(field, "")).strip() == normalized[field]
                    for field in REQUIRED_FIELDS
                )
                if same_payload:
                    return existing, f"订单编号 {order_no} 已存在，未重复创建，已返回原订单"
                return None, f"订单编号 {order_no} 已存在，请核对编号后再提交"

            entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
            entry.update(normalized)
            entry["status"] = STATUS_ORDER[0]
            entry["pending"] = True
            entry["abnormal"] = False
            rows.append(entry)
            return entry, "冷链订单已登记"

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"冷链订单 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于冷链订单可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"冷链订单已{action}"
