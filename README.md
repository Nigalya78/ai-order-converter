
An AI-powered order processing system that converts conversational, informal customer messages (WhatsApp, SMS, chat) into structured, validated snack orders.

Built with **FastAPI**, **Ollama (Llama 3.1)**, **SQLAlchemy**, **Neon PostgreSQL**, and a **React 19 + Vite + Tailwind CSS** frontend.

---

```
                      ┌──────────────────────────────────────┐
                      │   React + Vite Frontend (Port 5173)  │
                      │   - Dashboard & Operations Analytics │
                      │   - Orders Registry & Detail View    │
                      │   - AI Message-to-Order Playground   │
                      │   - Dynamic Catalog & WhatsApp Share │
                      └──────────────────┬───────────────────┘
                                         │ HTTP (JSON / REST)
                                         ▼
                      ┌──────────────────────────────────────┐
                      │      FastAPI Backend (Port 8000)     │
                      │   - Hybrid Bidirectional Rule Parser │
                      │   - Colloquial & Tanglish Normalizer │
                      │   - Pricing & Catalog Engine         │
                      │   - Ollama Llama 3.1 Extraction      │
                      │   - Analytics & Receipt Formatter    │
                      └───────────┬──────────────┬───────────┘
                                  │              │
                   ┌──────────────▼───┐       ┌──▼───────────────────┐
                   │  Ollama / LLM    │       │  Neon PostgreSQL DB  │
                   │  (Llama 3.1)     │       │  orders table        │
                   └──────────────────┘       └──────────────────────┘
```

---

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/extract` | Parses customer message into order, enquiry, or clarification using hybrid rule + LLM. Saves order to DB when valid. |
| `GET` | `/catalog` | Returns the recognized snack product catalogue, categories, descriptions, and variants. |
| `GET` | `/orders` | Lists all orders (supports `?status=...` and `?search=...`). |
| `GET` | `/orders/stats` | Returns operational and financial analytics (revenue, order counts, average order value, top snacks). |
| `GET` | `/orders/{order_id}` | Retrieves full order details by ID. |
| `GET` | `/orders/{order_id}/receipt` | Generates formatted customer WhatsApp receipt and direct share link. |
| `PATCH` | `/orders/{order_id}/status` | Updates order status (`payment_pending` ➔ `confirmed` or `cancelled`; `confirmed` ➔ `cancelled`). |
| `PATCH` | `/orders/{order_id}/items` | Updates line items directly (`add` or `replace` mode). Restricted to `payment_pending`. |
| `PATCH` | `/orders/{order_id}/modify-message` | Applies natural language modification message with multi-turn clarification support. Restricted to `payment_pending`. |

---

Configured in `app/catalog.py`:
- **Murukku** (Savory): 250g (₹150), 500g (₹290), 1kg (₹560)
- **Thattai** (Savory): 250g (₹160), 500g (₹310), 1kg (₹600)
- **Madras Mixture** (Savory): 250g (₹140), 500g (₹270), 1kg (₹520)
- **Mothichoor Laddu** (Sweet): 250g (₹180), 500g (₹350), 1kg (₹680)

---
```env
DATABASE_URL=postgresql://<user>:<password>@<neon-host>/<db-name>?sslmode=require
```
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```
> **Security Note:** Database credentials, Neon secrets, and Ollama credentials remain exclusively on the backend server and are never exposed to the frontend.

---

Make sure your virtual environment is activated and dependencies are installed:

```bash
venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify backend health:
- Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- API Base: [http://127.0.0.1:8000/orders](http://127.0.0.1:8000/orders)
- Stats Endpoint: [http://127.0.0.1:8000/orders/stats](http://127.0.0.1:8000/orders/stats)
- Catalog Endpoint: [http://127.0.0.1:8000/catalog](http://127.0.0.1:8000/catalog)

```bash
cd frontend
npm install
npm run dev
```

Open your browser at:
**[http://localhost:5173](http://localhost:5173)**

---

```bash
cd frontend
npm run build
```
Build output is generated cleanly into `frontend/dist/`.
To preview the production bundle locally:
```bash
npm run preview
```
