
Modern SaaS dashboard for the AI Customer Message-to-Order Converter backend.
- **React 19**
- **Vite 6**
- **TypeScript**
- **Tailwind CSS v4**
- **Lucide React** (icons)
```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts              # Typed API client calling FastAPI
│   │   └── types.ts               # Request & response types matching backend schemas
│   ├── components/
│   │   ├── common/
│   │   │   ├── AlertBanner.tsx    # Success / error alert notifications
│   │   │   ├── LoadingSpinner.tsx # Clean loading indicator
│   │   │   ├── Modal.tsx          # Accessible modal dialog container
│   │   │   └── StatusBadge.tsx    # Visual status pills for orders
│   │   ├── dashboard/
│   │   │   └── StatCard.tsx       # Metrics KPI cards
│   │   ├── layout/
│   │   │   ├── Header.tsx         # Top bar with actions and refresh
│   │   │   ├── Layout.tsx         # Main responsive layout container
│   │   │   └── Sidebar.tsx        # Side navigation with API connection indicator
│   │   └── orders/
│   │       ├── OrderDetail.tsx    # Line items & customer message audit log
│   │       ├── OrderModifyModal.tsx # AI natural message & structured item modification
│   │       ├── OrderStatusModal.tsx # Status transition modal adhering to DB rules
│   │       └── OrdersTable.tsx    # Filterable & searchable order registry
│   ├── pages/
│   │   ├── CatalogPage.tsx        # Read-only snack catalog reference
│   │   ├── DashboardPage.tsx      # Overview metrics & pipeline distribution
│   │   ├── MessageToOrderPage.tsx # AI customer message converter
│   │   ├── OrderDetailPage.tsx    # Single order management page
│   │   └── OrdersPage.tsx         # Orders table management view
│   ├── App.tsx                    # Root routing and state coordination
│   ├── index.css                  # Tailwind CSS styling
│   └── main.tsx                   # Application bootstrap
├── .env.example
├── .env
├── package.json
├── tsconfig.json
└── vite.config.ts
```

```bash
npm install
npm run dev
npm run build
```
