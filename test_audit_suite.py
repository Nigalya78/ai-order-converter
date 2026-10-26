import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.text_normalizer import normalize_message
from app.product_matcher import match_product_name
from app.rule_parser import parse_simple_order
from app.llm_service import extract, _heuristic_fallback
from app.database import get_orders, get_order_by_id

client = TestClient(app)


class AuditTestSuite(unittest.TestCase):
    def test_01_normalization_fractions(self):
        """Verify fractional and colloquial quantity normalization."""
        self.assertEqual(normalize_message("half kg murukku"), "500g murukku")
        self.assertEqual(normalize_message("ara kg laddu"), "500g laddu")
        self.assertEqual(normalize_message("arakilo thattai"), "500g thattai")
        self.assertEqual(normalize_message("kaal kg mixture"), "250g mixture")
        self.assertEqual(normalize_message("kaalkilo laddu"), "250g laddu")
        self.assertEqual(normalize_message("quarter kg murukku"), "250g murukku")
        self.assertEqual(normalize_message("mukkaal kg laddu"), "750g laddu")
        self.assertEqual(normalize_message("1/2 kg murukku"), "500g murukku")
        self.assertEqual(normalize_message("1/4 kg thattai"), "250g thattai")

    def test_01_normalization_numbers_and_units(self):
        """Verify number words and unit standardizations."""
        self.assertEqual(normalize_message("oru kg laddu"), "1kg laddu")
        self.assertEqual(normalize_message("rendu kg murukku"), "2kg murukku")
        self.assertEqual(normalize_message("500 grams murukku"), "500g murukku")
        self.assertEqual(normalize_message("250 gms mixture"), "250g mixture")
        self.assertEqual(normalize_message("2 kgs laddu"), "2kg laddu")
        self.assertEqual(normalize_message("1 kilo thattai"), "1kg thattai")

    def test_01_product_matching(self):
        """Verify fuzzy product matching and colloquial synonyms."""
        self.assertEqual(match_product_name("murukku"), "murukku")
        self.assertEqual(match_product_name("muruku"), "murukku")
        self.assertEqual(match_product_name("chakli"), "murukku")
        self.assertEqual(match_product_name("thatai"), "thattai")
        self.assertEqual(match_product_name("thattuvadai"), "thattai")
        self.assertEqual(match_product_name("laddoo"), "laddu")
        self.assertEqual(match_product_name("ladu"), "laddu")
        self.assertEqual(match_product_name("mix"), "mixture")
        self.assertEqual(match_product_name("madras mixture"), "mixture")
        self.assertIsNone(match_product_name("pizza"))
        self.assertIsNone(match_product_name(""))
    def test_02_rule_parser_bidirectional(self):
        """Verify fast deterministic parsing without LLM roundtrip."""
        r1 = parse_simple_order("500g murukku")
        self.assertIsNotNone(r1)
        self.assertEqual(r1["intent"], "new_order")
        self.assertEqual(r1["items"][0]["product"], "murukku")
        self.assertEqual(r1["items"][0]["quantity"], 500.0)
        self.assertEqual(r1["items"][0]["unit"], "g")
        r2 = parse_simple_order("laddu 1kg")
        self.assertIsNotNone(r2)
        self.assertEqual(r2["intent"], "new_order")
        self.assertEqual(r2["items"][0]["product"], "laddu")
        self.assertEqual(r2["items"][0]["quantity"], 1.0)
        self.assertEqual(r2["items"][0]["unit"], "kg")
        r3 = parse_simple_order("mixture 250g and murukku 500g")
        self.assertIsNotNone(r3)
        self.assertEqual(r3["intent"], "new_order")
        self.assertEqual(len(r3["items"]), 2)
        products = {it["product"]: it["quantity"] for it in r3["items"]}
        self.assertEqual(products.get("mixture"), 250.0)
        self.assertEqual(products.get("murukku"), 500.0)
        r4 = parse_simple_order("What is the price of thattai 500g?")
        self.assertIsNotNone(r4)
        self.assertEqual(r4["intent"], "product_enquiry")

    def test_02_ollama_offline_fallback(self):
        """Verify extract() gracefully recovers when Ollama raises an exception."""
        with patch("ollama.chat", side_effect=ConnectionError("Could not connect to Ollama")):
            res1 = extract("I want some murukku")
            self.assertEqual(res1.intent, "new_order")
            self.assertTrue(res1.needs_clarification)
            self.assertIn("murukku", res1.clarification_question or "")
            res2 = extract("How much is laddu?")
            self.assertEqual(res2.intent, "product_enquiry")
            self.assertEqual(len(res2.items), 1)
            self.assertEqual(res2.items[0].product, "laddu")
            res3 = extract("Please cancel order")
            self.assertEqual(res3.intent, "cancel_order")
            res4 = extract("Hello there")
            self.assertEqual(res4.intent, "unclear")
            self.assertTrue(res4.needs_clarification)
    def test_03_get_catalog(self):
        """Verify GET /catalog returns all 4 products with valid schema."""
        resp = client.get("/catalog")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("products", data)
        self.assertEqual(len(data["products"]), 4)

        for prod in data["products"]:
            self.assertIn("id", prod)
            self.assertIn("name", prod)
            self.assertIn("category", prod)
            self.assertIn("description", prod)
            self.assertIn("variants", prod)
            self.assertGreater(len(prod["variants"]), 0)
            for v in prod["variants"]:
                self.assertIn("size", v)
                self.assertIn("price", v)
                self.assertIsInstance(v["price"], (int, float))
    def test_04_get_orders_stats(self):
        """Verify GET /orders/stats calculates operational KPIs."""
        resp = client.get("/orders/stats")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()
        required_keys = [
            "total_orders",
            "pending_orders",
            "confirmed_orders",
            "cancelled_orders",
            "total_revenue",
            "confirmed_revenue",
            "avg_order_value",
            "top_products",
        ]
        for key in required_keys:
            self.assertIn(key, stats)

        self.assertIsInstance(stats["total_orders"], int)
        self.assertIsInstance(stats["total_revenue"], (int, float))
        self.assertIsInstance(stats["top_products"], list)
    def test_05_order_filtering_and_search(self):
        """Verify GET /orders with status and search parameters."""
        resp_pending = client.get("/orders?status=payment_pending")
        self.assertEqual(resp_pending.status_code, 200)
        for ord_item in resp_pending.json()["orders"]:
            self.assertEqual(ord_item["status"], "payment_pending")

        resp_confirmed = client.get("/orders?status=confirmed")
        self.assertEqual(resp_confirmed.status_code, 200)
        for ord_item in resp_confirmed.json()["orders"]:
            self.assertEqual(ord_item["status"], "confirmed")
        resp_invalid = client.get("/orders?status=invalid_xyz")
        self.assertEqual(resp_invalid.status_code, 400)
        resp_search = client.get("/orders?search=murukku")
        self.assertEqual(resp_search.status_code, 200)
        self.assertIn("orders", resp_search.json())
        resp_empty = client.get("/orders?search=NON_EXISTENT_SNACK_KEYWORD_XYZ")
        self.assertEqual(resp_empty.status_code, 200)
        self.assertEqual(resp_empty.json()["count"], 0)
    def test_06_whatsapp_receipt_generation(self):
        """Verify GET /orders/{order_id}/receipt returns formatted text and share URL."""
        orders_resp = client.get("/orders")
        orders = orders_resp.json()["orders"]
        if not orders:
            self.skipTest("No orders available in database to test receipt generation")

        sample_order_id = orders[0]["order_id"]
        resp = client.get(f"/orders/{sample_order_id}/receipt")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["order_id"], sample_order_id)
        self.assertIn("receipt", data)
        self.assertIn("whatsapp_url", data)
        self.assertIn("AI Snack Order Confirmation", data["receipt"])
        self.assertIn(f"#{sample_order_id}", data["receipt"])
        self.assertTrue(data["whatsapp_url"].startswith("https://wa.me/?text="))
        resp_404 = client.get("/orders/99999999/receipt")
        self.assertEqual(resp_404.status_code, 404)
    def test_08_order_lifecycle_persistence(self):
        """Full end-to-end order lifecycle: Create -> Read -> Modify -> Status transition."""
        create_payload = {"message": "I need 500g thattai and 250g mixture"}
        create_resp = client.post("/extract", json=create_payload)
        self.assertEqual(create_resp.status_code, 200)
        created_data = create_resp.json()

        self.assertTrue(created_data["order"]["valid"])
        order_id = created_data["order_id"]
        self.assertIsNotNone(order_id)
        self.assertEqual(created_data["status"], "payment_pending")
        read_resp = client.get(f"/orders/{order_id}")
        self.assertEqual(read_resp.status_code, 200)
        read_order = read_resp.json()
        self.assertEqual(read_order["order_id"], order_id)
        self.assertEqual(read_order["status"], "payment_pending")
        self.assertEqual(len(read_order["items"]), 2)
        initial_total = read_order["total"]
        modify_items_payload = {
            "customer_message": "Added 250g murukku via audit test",
            "items": [{"product": "murukku", "quantity": 250, "unit": "g"}],
            "action": "add",
        }
        mod_resp = client.patch(f"/orders/{order_id}/items", json=modify_items_payload)
        self.assertEqual(mod_resp.status_code, 200)
        mod_data = mod_resp.json()
        self.assertEqual(len(mod_data["items"]), 3)
        self.assertGreater(mod_data["total"], initial_total)
        mod_msg_payload = {"message": "add 500g murukku"}
        mod_msg_resp = client.patch(f"/orders/{order_id}/modify-message", json=mod_msg_payload)
        self.assertEqual(mod_msg_resp.status_code, 200)
        status_resp1 = client.patch(f"/orders/{order_id}/status", json={"status": "confirmed"})
        self.assertEqual(status_resp1.status_code, 200)
        blocked_mod = client.patch(f"/orders/{order_id}/items", json=modify_items_payload)
        self.assertEqual(blocked_mod.status_code, 400)
        self.assertIn("Only payment-pending orders can be modified", blocked_mod.json()["detail"])
        status_resp2 = client.patch(f"/orders/{order_id}/status", json={"status": "cancelled"})
        self.assertEqual(status_resp2.status_code, 200)
        blocked_status = client.patch(f"/orders/{order_id}/status", json={"status": "confirmed"})
        self.assertEqual(blocked_status.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
