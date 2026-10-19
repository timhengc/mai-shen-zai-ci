import json
import unittest
from decimal import Decimal

from mcd_life_kit.annual_report import collect_orders, normalize_order, render_html, summarize
from mcd_life_kit.mcp_client import MCPClient, MCPError


def order(id="a", **changes):
    return dict(orderId=id, createTime=changes.pop("createTime", "2026-01-02 18:00:00"),
                orderStatus=changes.pop("orderStatus", "订单已完成"), realTotalAmount=changes.pop("realTotalAmount", "13.90"),
                orderProductList=changes.pop("orderProductList", [{"productName": "套餐", "quantity": 2,
                    "comboItemList": [{"name": "小薯条", "quantity": 1}, {"name": "可乐", "quantity": 1}]}]), **changes)


class AnnualReportTests(unittest.TestCase):
    def test_real_schema_combo_and_decimal(self):
        report = summarize([order(), order("b", realTotalAmount="9")], 2026)
        self.assertEqual(report["count"], 2)
        self.assertEqual(Decimal(report["amount"]), Decimal("22.90"))
        self.assertEqual(report["top_foods"], [{"name": "小薯条", "quantity": 4}, {"name": "可乐", "quantity": 4}])

    def test_dedup_status_timezone_year(self):
        data = [order(), order(), order("b", orderStatus="已取消"), order("c", orderStatus="99"),
                order("d", createTime="2025-12-31T16:30:00Z"), order("e", createTime="2025-03-01"),
                order("f", createTime="bad"), order("")]
        report = summarize(data, 2026)
        self.assertEqual(report["count"], 2)
        self.assertEqual(report["excluded"], 2)
        self.assertEqual(report["deduplicated"], 1)
        self.assertEqual(report["first"], "2026-01-01")
        self.assertEqual(report["hours"][0], 1)
        self.assertTrue(any("缺少订单标识" in note for note in report["notes"]))

    def test_missing_amount_never_zero_and_empty(self):
        report = summarize([order(realTotalAmount="unknown")], 2026)
        self.assertIsNone(report["amount"])
        self.assertEqual(report["amount_count"], 0)
        self.assertIsNone(summarize([], 2026)["first"])
        self.assertEqual(normalize_order(order(realTotalAmount=None, payAmountFen=1390))["amount"], "13.90")

    def test_html_escapes_script_breakout_and_omits_identifiers(self):
        report = summarize([order("private-order-id", phone="13800000000", address="private-address")], 2026)
        result = render_html(report, "</script><img src=x onerror=alert(1)>")
        self.assertNotIn("</script><img", result)
        self.assertNotIn("private-order-id", result)
        self.assertNotIn("13800000000", result)
        self.assertNotIn("private-address", result)
        self.assertNotIn("__REPORT_JSON__", result)

    def test_pagination_reads_schema_and_does_not_stop_on_short_page(self):
        class Fake:
            calls = []
            def list_tools(self):
                return [{"name": "order-list", "inputSchema": {"properties": {"pageNo": {"type": "integer"}, "pageSize": {"maximum": 50}}}}]
            def call_tool(self, name, args):
                self.calls.append((name, args))
                return {"data": {"list": [order(str(args["pageNo"]))], "total": 2}}
        client = Fake()
        data, warnings = collect_orders(client)
        self.assertEqual(len(data), 2)
        self.assertEqual(warnings, [])
        self.assertEqual(client.calls[1], ("order-list", {"pageNo": 2, "pageSize": 50}))

    def test_repeated_page_and_business_errors(self):
        class Fake:
            def list_tools(self):
                return [{"name": "order-list", "inputSchema": {"properties": {"page": {}}}}]
            def call_tool(self, name, args):
                return {"data": {"list": [order()]}}
        data, warnings = collect_orders(Fake())
        self.assertEqual(len(data), 1)
        self.assertIn("重复", warnings[0])
        from mcd_life_kit.annual_report import records
        with self.assertRaises(MCPError):
            records({"success": False, "code": 401, "data": []})
        with self.assertRaises(MCPError):
            records({"success": True, "data": {"unexpected": []}})

    def test_mcp_tool_error_not_a_report(self):
        client = MCPClient(token="test")
        client._rpc = lambda *a, **kw: {"isError": True, "content": [{"type": "text", "text": "failed"}]}
        with self.assertRaises(MCPError):
            client.call_tool("order-list")


if __name__ == "__main__":
    unittest.main()
