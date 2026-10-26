import sys
import unittest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.catalog import PRODUCT_CATALOG
from app.database import (
    create_or_get_chat_session,
    get_chat_session,
    get_chat_messages,
    get_order_by_id,
    update_order_status,
)

client = TestClient(app)


class ConversationalChatTestSuite(unittest.TestCase):
    """
    Automated test suite verifying the Conversational AI Chat-to-Order system
    against all requirements specified in Section 4.
    """

    def setUp(self):
        self.session_id = f"test-session-{uuid.uuid4()}"

    def test_01_new_conversation_receives_session_id(self):
        """1. A new conversation receives a session ID."""
        resp = client.post("/chat", json={"session_id": None, "message": "Hi, what snacks do you have?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("session_id", data)
        self.assertTrue(len(data["session_id"]) > 0)
        self.assertIn("Murukku", data["reply"])

    def test_02_product_enquiries_return_actual_catalogue_info(self):
        """2. Product enquiries return actual catalogue information."""
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "What is the price of 500g murukku?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        murukku_500g_price = PRODUCT_CATALOG["murukku"]["variants"]["500g"]
        self.assertIn(str(murukku_500g_price), data["reply"])
        self.assertEqual(data["intent"], "product_enquiry")

    def test_03_extraction_reuses_converter(self):
        """3. Product and quantity extraction reuses the existing converter."""
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "Add 500g murukku"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["cart"]["items"]), 1)
        self.assertEqual(data["cart"]["items"][0]["product"], "murukku")
        self.assertEqual(data["cart"]["items"][0]["quantity"], 500.0)
        self.assertEqual(data["cart"]["items"][0]["price"], 290.0)

    def test_04_multiple_messages_preserve_context(self):
        """4. Multiple messages preserve conversation context."""
        client.post("/chat", json={"session_id": self.session_id, "message": "What is the price of thattai 500g?"})
        session = get_chat_session(self.session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session["context"].get("last_discussed_product"), "thattai")
        messages = get_chat_messages(self.session_id)
        self.assertGreaterEqual(len(messages), 2)  # Customer + Assistant

    def test_05_followup_reference_add_that_too(self):
        """5. Follow-up references such as 'add that too' work correctly when unambiguous."""
        client.post("/chat", json={"session_id": self.session_id, "message": "What is the price of 250g mixture?"})
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "add that"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["cart"]["items"]), 1)
        self.assertEqual(data["cart"]["items"][0]["product"], "mixture")
        self.assertEqual(data["cart"]["items"][0]["quantity"], 250.0)
        self.assertEqual(data["cart"]["items"][0]["price"], 140.0)

    def test_06_missing_quantities_trigger_clarification(self):
        """6. Missing quantities trigger clarification rather than an incorrect order."""
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "I need some laddu"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "clarification_needed")
        self.assertEqual(len(data["cart"]["items"]), 0)
        self.assertIn("size", data["reply"].lower())

    def test_07_cart_totals_calculated_by_backend(self):
        """7. Cart totals are calculated strictly by the backend."""
        client.post("/chat", json={"session_id": self.session_id, "message": "add 500g murukku"})
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "add 250g laddu"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["cart"]["total"], 470.0)

    def test_08_draft_carts_survive_page_refresh(self):
        """8. Draft carts survive a page refresh (retrieved via GET /chat/sessions/{session_id})."""
        client.post("/chat", json={"session_id": self.session_id, "message": "add 1kg murukku"})
        resp = client.get(f"/chat/sessions/{self.session_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session_id"], self.session_id)
        self.assertEqual(len(data["cart"]["items"]), 1)
        self.assertEqual(data["cart"]["items"][0]["product"], "murukku")
        self.assertEqual(data["cart"]["total"], 560.0)

    def test_09_orders_not_created_before_explicit_confirmation(self):
        """9. Orders are not created before explicit confirmation."""
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "add 500g thattai"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["order_id"])

        session = get_chat_session(self.session_id)
        self.assertIsNone(session["created_order_id"])

    def test_10_and_11_confirmation_creates_exactly_one_order_and_is_idempotent(self):
        """
        10. Confirming a draft creates exactly one order.
        11. Duplicate confirmation requests do not create duplicate orders.
        """
        client.post("/chat", json={"session_id": self.session_id, "message": "add 250g thattai"})
        confirm_resp1 = client.post("/chat", json={"session_id": self.session_id, "message": "yes, place order"})
        self.assertEqual(confirm_resp1.status_code, 200)
        data1 = confirm_resp1.json()
        order_id_1 = data1["order_id"]
        self.assertIsNotNone(order_id_1)
        self.assertEqual(data1["intent"], "order_placed")
        order_in_db = get_order_by_id(order_id_1)
        self.assertIsNotNone(order_in_db)
        self.assertEqual(order_in_db["status"], "payment_pending")
        confirm_resp2 = client.post("/chat", json={"session_id": self.session_id, "message": "yes please"})
        self.assertEqual(confirm_resp2.status_code, 200)
        data2 = confirm_resp2.json()
        order_id_2 = data2["order_id"]
        self.assertEqual(order_id_1, order_id_2)

    def test_12_existing_pending_order_modification_enforced(self):
        """12. Existing pending-order modification rules remain enforced."""
        ext_resp = client.post("/extract", json={"message": "500g murukku"})
        created_id = ext_resp.json()["order_id"]
        self.assertIsNotNone(created_id)
        mod_resp = client.patch(
            f"/orders/{created_id}/items",
            json={"customer_message": "Add 250g mixture", "items": [{"product": "mixture", "quantity": 250, "unit": "g"}], "action": "add"},
        )
        self.assertEqual(mod_resp.status_code, 200)
        self.assertEqual(len(mod_resp.json()["items"]), 2)

    def test_13_invalid_order_transitions_remain_rejected(self):
        """13. Invalid order transitions remain rejected."""
        ext_resp = client.post("/extract", json={"message": "500g murukku"})
        created_id = ext_resp.json()["order_id"]
        client.patch(f"/orders/{created_id}/status", json={"status": "cancelled"})
        invalid_resp = client.patch(f"/orders/{created_id}/status", json={"status": "confirmed"})
        self.assertEqual(invalid_resp.status_code, 400)

    def test_14_sessions_are_isolated(self):
        """14. Conversation sessions are strictly isolated."""
        session_a = f"test-user-a-{uuid.uuid4()}"
        session_b = f"test-user-b-{uuid.uuid4()}"
        client.post("/chat", json={"session_id": session_a, "message": "add 500g murukku"})
        client.post("/chat", json={"session_id": session_b, "message": "add 1kg laddu"})

        cart_a = client.get(f"/chat/sessions/{session_a}").json()["cart"]
        cart_b = client.get(f"/chat/sessions/{session_b}").json()["cart"]
        self.assertEqual(len(cart_a["items"]), 1)
        self.assertEqual(cart_a["items"][0]["product"], "murukku")
        self.assertEqual(cart_a["total"], 290.0)

        self.assertEqual(len(cart_b["items"]), 1)
        self.assertEqual(cart_b["items"][0]["product"], "laddu")
        self.assertEqual(cart_b["total"], 680.0)

    def test_15_ollama_offline_safe_handling(self):
        """15. Errors from Ollama are handled safely without crashing."""
        with patch("ollama.chat", side_effect=ConnectionError("Ollama daemon down")):
            resp = client.post("/chat", json={"session_id": self.session_id, "message": "I want to try snacks"})
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Murukku", resp.json()["reply"])

    def test_16_bug1_multi_item_extraction_unconfigured_variant(self):
        """BUG 1: Recognize multiple items, add only configured variants, flag unconfigured sizes."""
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "muruku 250g thattai 100g"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["cart"]["items"]), 1)
        self.assertEqual(data["cart"]["items"][0]["product"], "murukku")
        self.assertEqual(data["cart"]["items"][0]["quantity"], 250.0)
        self.assertEqual(data["cart"]["total"], 150.0)
        self.assertIn("Thattai 100g", data["reply"])
        self.assertIn("not a configured size", data["reply"].lower())

    def test_17_bug2_customer_corrections_reconciliation(self):
        """BUG 2: Customer correction reconciles cart without duplicate lines."""
        client.post("/chat", json={"session_id": self.session_id, "message": "muruku 250g thattai 100g"})
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "I told you Murukku 250g and Thattai 100g."})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["cart"]["items"]), 1)
        self.assertEqual(data["cart"]["items"][0]["product"], "murukku")
        self.assertEqual(data["cart"]["items"][0]["quantity"], 250.0)
        self.assertEqual(data["cart"]["total"], 150.0)

    def test_18_bug3_remove_incorrect_items_dispute(self):
        """BUG 3: Disputing an erroneously added item removes it and preserves valid items."""
        client.post("/chat", json={"session_id": self.session_id, "message": "add 250g murukku"})
        client.post("/chat", json={"session_id": self.session_id, "message": "add 250g thattai"})
        cart_before = client.get(f"/chat/sessions/{self.session_id}").json()["cart"]
        self.assertEqual(len(cart_before["items"]), 2)

        resp = client.post("/chat", json={"session_id": self.session_id, "message": "I didn't even tell you Thattai 250g."})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "dispute_resolved")
        self.assertEqual(len(data["cart"]["items"]), 1)
        self.assertEqual(data["cart"]["items"][0]["product"], "murukku")
        self.assertEqual(data["cart"]["total"], 150.0)

    def test_19_bug4_frustration_de_escalation(self):
        """BUG 4: Frustration detection politely acknowledges misunderstanding with order context."""
        client.post("/chat", json={"session_id": self.session_id, "message": "muruku 250g thattai 100g"})
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "idiot"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "frustration_handled")
        self.assertIn("Sorry", data["reply"])
        self.assertIn("Murukku 250g", data["reply"])

    def test_20_category_enquiry_sweet_vs_savory(self):
        """Category enquiry distinguishes sweet vs savory."""
        resp_sweet = client.post("/chat", json={"session_id": self.session_id, "message": "sweet varietes"})
        self.assertEqual(resp_sweet.status_code, 200)
        data_sweet = resp_sweet.json()
        self.assertIn("Laddu", data_sweet["reply"])

        resp_savory = client.post("/chat", json={"session_id": self.session_id, "message": "savory snacks"})
        self.assertEqual(resp_savory.status_code, 200)
        data_savory = resp_savory.json()
        self.assertIn("Murukku", data_savory["reply"])
        self.assertIn("Thattai", data_savory["reply"])

    def test_21_product_description_enquiry(self):
        """Customer asks 'what laddu is this'."""
        client.post("/chat", json={"session_id": self.session_id, "message": "add 500g laddu"})
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "what laddu is this"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Mothichoor Laddu", data["reply"])
        self.assertIn("Sweet", data["reply"])

    def test_22_wrap_up_ready_to_order(self):
        """Customer says 'nothing else i need' when cart has items."""
        client.post("/chat", json={"session_id": self.session_id, "message": "add 500g laddu"})
        resp = client.post("/chat", json={"session_id": self.session_id, "message": "nothing else i need"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "wrap_up_ready")
        self.assertTrue(data["pending_confirmation"])
        self.assertIn("350", data["reply"])

    def test_23_enquiry_followup_yess_add(self):
        """Customer asks price of 500g murukku then answers 'yess add'."""
        r1 = client.post("/chat", json={"session_id": self.session_id, "message": "What is the price of 500g murukku?"})
        self.assertEqual(r1.status_code, 200)
        self.assertIn("290", r1.json()["reply"])

        r2 = client.post("/chat", json={"session_id": self.session_id, "message": "yess add"})
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertEqual(len(data["cart"]["items"]), 1)
        self.assertEqual(data["cart"]["items"][0]["product"], "murukku")
        self.assertEqual(data["cart"]["items"][0]["quantity"], 500.0)
        self.assertEqual(data["cart"]["items"][0]["price"], 290.0)
        self.assertIn("Added", data["reply"])

    def test_24_enquiry_followup_affirmative_yes(self):
        """Customer asks price of 250g mixture then answers 'yes' to add it."""
        sid = f"test-yes-{uuid.uuid4()}"
        r1 = client.post("/chat", json={"session_id": sid, "message": "What is the price of 250g mixture?"})
        self.assertEqual(r1.status_code, 200)
        self.assertIn("140", r1.json()["reply"])

        r2 = client.post("/chat", json={"session_id": sid, "message": "yes"})
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertEqual(len(data["cart"]["items"]), 1)
        self.assertEqual(data["cart"]["items"][0]["product"], "mixture")
        self.assertEqual(data["cart"]["items"][0]["quantity"], 250.0)
        self.assertEqual(data["cart"]["items"][0]["price"], 140.0)


if __name__ == "__main__":
    unittest.main()
