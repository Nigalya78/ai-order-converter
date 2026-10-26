import React, { useState, useEffect } from 'react';
import { Tag, Search, RefreshCw, ShoppingCart, HelpCircle } from 'lucide-react';
import type { ProductCatalogItem } from '../api/types';
import api from '../api/client';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

interface CatalogPageProps {
  onSelectSampleMessage: (sampleText: string) => void;
}

const FALLBACK_CATALOG: ProductCatalogItem[] = [
  {
    id: 'murukku',
    name: 'Murukku',
    category: 'Savory',
    description: 'Traditional South Indian spiral snack prepared from premium rice flour, roasted urad dal, and sesame seeds.',
    variants: [
      { size: '250g', price: 150 },
      { size: '500g', price: 290 },
      { size: '1kg', price: 560 },
    ],
  },
  {
    id: 'thattai',
    name: 'Thattai',
    category: 'Savory',
    description: 'Crispy, flat disc snack crafted from spiced rice batter, Bengal gram, and fragrant curry leaves.',
    variants: [
      { size: '250g', price: 160 },
      { size: '500g', price: 310 },
      { size: '1kg', price: 600 },
    ],
  },
  {
    id: 'mixture',
    name: 'Madras Mixture',
    category: 'Savory',
    description: 'Crunchy medley of spiced sev, boondi, roasted peanuts, fried dal, and aromatic curry leaves.',
    variants: [
      { size: '250g', price: 140 },
      { size: '500g', price: 270 },
      { size: '1kg', price: 520 },
    ],
  },
  {
    id: 'laddu',
    name: 'Mothichoor Laddu',
    category: 'Sweet',
    description: 'Authentic festive sweet spheres made of golden gram flour pearls simmered in ghee and cardamom syrup.',
    variants: [
      { size: '250g', price: 180 },
      { size: '500g', price: 350 },
      { size: '1kg', price: 680 },
    ],
  },
];

export const CatalogPage: React.FC<CatalogPageProps> = ({ onSelectSampleMessage }) => {
  const [products, setProducts] = useState<ProductCatalogItem[]>(FALLBACK_CATALOG);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<'All' | 'Savory' | 'Sweet'>('All');

  const fetchCatalog = async () => {
    setIsLoading(true);
    try {
      const res = await api.getCatalog();
      if (res.products && res.products.length > 0) {
        setProducts(res.products);
      }
    } catch {
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalog();
  }, []);

  const filteredProducts = products.filter((p) => {
    const matchesCat = selectedCategory === 'All' || p.category === selectedCategory;
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Product Catalogue</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Recognized snacks, weight variants, and dynamic pricing powered by FastAPI
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter snacks..."
              className="pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <button
            type="button"
            onClick={fetchCatalog}
            disabled={isLoading}
            className="p-1.5 text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            title="Refresh catalog from API"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin text-indigo-600' : ''} />
          </button>
        </div>
      </div>

      {}
      <div className="flex items-center gap-2">
        {(['All', 'Savory', 'Sweet'] as const).map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1 text-xs font-semibold rounded-lg transition-colors ${
              selectedCategory === cat
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            {cat} Snacks
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="py-12 flex justify-center">
          <LoadingSpinner size="md" label="Loading product catalog..." />
        </div>
      )}

      {}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filteredProducts.map((snack) => (
          <div
            key={snack.id}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
                    <Tag size={16} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 leading-tight">
                      {snack.name}
                    </h3>
                    <span className="text-[11px] font-medium text-slate-400">
                      ID: <code className="font-mono text-indigo-600">{snack.id}</code> ·{' '}
                      <span className="capitalize">{snack.category}</span>
                    </span>
                  </div>
                </div>

                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                  {snack.variants.length} Sizes
                </span>
              </div>

              <p className="text-xs text-slate-600 mt-3 leading-relaxed">{snack.description}</p>

              {}
              <div className="mt-4 space-y-1.5">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Available Package Variants
                </span>
                <div className="grid grid-cols-3 gap-2">
                  {snack.variants.map((v) => (
                    <div
                      key={v.size}
                      className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 text-center hover:bg-indigo-50/50 hover:border-indigo-200 transition-colors"
                    >
                      <span className="text-xs font-medium text-slate-600 block">{v.size}</span>
                      <span className="text-sm font-extrabold text-slate-900">₹{v.price}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {}
            <div className="mt-5 pt-3.5 border-t border-slate-100 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() =>
                  onSelectSampleMessage(`What is the price of ${snack.id} 500g?`)
                }
                className="text-xs text-slate-600 hover:text-indigo-600 font-medium flex items-center gap-1 transition-colors"
              >
                <HelpCircle size={13} />
                <span>Ask Price</span>
              </button>

              <button
                type="button"
                onClick={() =>
                  onSelectSampleMessage(`I want 500g ${snack.id} and 1kg laddu`)
                }
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-3.5 py-1.5 rounded-lg shadow-xs transition-colors"
              >
                <ShoppingCart size={13} />
                <span>Order via AI</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
