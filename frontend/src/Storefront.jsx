import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, CheckCircle2, Search, ShoppingBag, ShoppingCart, Store, X } from 'lucide-react';

const api = async (path, options = {}) => {
  const response = await fetch('/api' + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.error || 'Request failed (' + response.status + ')');
  return data;
};

const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value || 0));
const field = 'w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-3 text-sm text-white outline-none focus:border-cyan-400';
const button = 'inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 px-4 py-3 text-sm font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50 transition hover:bg-cyan-300';

export default function Storefront({ onBack }) {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [checkout, setCheckout] = useState(false);
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [customer, setCustomer] = useState({
    customer_name: '',
    phone: '',
    email: '',
    shipping_address: '',
    customer_note: ''
  });

  useEffect(() => {
    api('/store/catalog')
      .then(rows => setProducts(rows.filter(p => Number(p.price) > 0)))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(() => {
    const set = new Set();
    products.forEach(p => {
      if (p.category) set.add(p.category);
    });
    return ['All', ...Array.from(set)];
  }, [products]);

  const filteredProducts = useMemo(() => {
    return products.filter(p => {
      if (categoryFilter !== 'All' && String(p.category || '').toLowerCase() !== categoryFilter.toLowerCase()) {
        return false;
      }
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        const haystack = [p.name, p.category, p.brand, p.sku, p.package_type].filter(Boolean).join(' ').toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [products, categoryFilter, search]);

  const cartItems = useMemo(
    () => products.filter(p => cart[p.id] > 0).map(p => ({ ...p, quantity: cart[p.id] })),
    [products, cart]
  );
  const total = cartItems.reduce((sum, p) => sum + p.price * p.quantity, 0);
  const count = cartItems.reduce((sum, p) => sum + p.quantity, 0);

  const setQty = (id, value) => {
    const product = products.find(p => Number(p.id) === Number(id));
    const limit = Math.min(100, Math.max(0, Math.floor(Number(product?.available_stock || 0))));
    setCart(old => ({ ...old, [id]: Math.max(0, Math.min(limit, Number(value) || 0)) }));
  };

  const submit = async event => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await api('/store/orders', {
        method: 'POST',
        body: JSON.stringify({
          ...customer,
          items: cartItems.map(p => ({ product_id: p.id, quantity: p.quantity }))
        })
      });
      setReceipt(result);
      setCart({});
      setCheckout(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleReturn = () => {
    if (onBack) {
      onBack();
    } else {
      window.location.hash = '';
      window.location.pathname = '/';
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleReturn}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-white/10"
              title="Return to Employee Operations Portal"
            >
              <ArrowLeft size={15} /> Operations OS
            </button>
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan-400 text-slate-950">
                <Store size={20} />
              </span>
              <div>
                <strong className="block text-sm font-extrabold tracking-wide sm:text-base text-white">
                  USA–RAW STRENGTH
                </strong>
                <span className="text-xs text-slate-400">United Sciences Alliance · Official Store</span>
              </div>
            </div>
          </div>
          <button
            className="relative inline-flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-sm font-semibold hover:border-cyan-400/40"
            onClick={() => setCheckout(true)}
          >
            <ShoppingCart size={17} /> Cart
            <span className="rounded-full bg-cyan-400 px-2 py-0.5 text-xs font-bold text-slate-950">
              {count}
            </span>
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <section className="mb-8 overflow-hidden rounded-3xl border border-cyan-300/15 bg-gradient-to-br from-cyan-950 via-slate-900 to-indigo-950 p-6 sm:p-10 shadow-2xl">
          <p className="text-xs font-bold uppercase tracking-[.25em] text-cyan-300">
            United Sciences Alliance presents
          </p>
          <h1 className="mt-3 max-w-2xl text-3xl font-black tracking-tight text-white sm:text-5xl">
            USA–Raw Strength Store
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">
            Explore the official USA–Raw Strength product catalog. Add authentic products to your cart and submit an order for immediate fulfillment by our team.
          </p>
          <div className="mt-6 flex flex-wrap gap-3 text-xs text-slate-300">
            <span className="rounded-full border border-white/15 px-3 py-1.5 bg-black/20">Official product catalog</span>
            <span className="rounded-full border border-white/15 px-3 py-1.5 bg-black/20">India · INR pricing</span>
            <span className="rounded-full border border-white/15 px-3 py-1.5 bg-black/20">Cash on delivery · Verified</span>
          </div>
        </section>

        {error && (
          <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-950/40 p-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {receipt && (
          <section className="mb-6 rounded-2xl border border-emerald-400/30 bg-emerald-950/30 p-5 shadow-xl">
            <div className="flex items-center gap-2 font-bold text-emerald-200 text-base">
              <CheckCircle2 size={20} /> Order request successfully received!
            </div>
            <p className="mt-1 text-sm text-slate-300">
              Your order code is <strong className="text-white text-base font-black">{receipt.order_code}</strong>. Total:{' '}
              <strong className="text-white font-bold">{money(receipt.total_amount)}</strong> (Cash on Delivery).
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Our operations team will confirm your order and contact you at {customer.phone || 'your phone number'}.
            </p>
            <button
              type="button"
              onClick={() => setReceipt(null)}
              className="mt-3 rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-400/20"
            >
              Place another order
            </button>
          </section>
        )}

        {/* Search and Category Bar */}
        <div className="mb-6 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="relative min-w-[260px] flex-1 max-w-md">
              <Search className="absolute left-3 top-3 text-slate-400" size={16} />
              <input
                className="w-full rounded-xl border border-white/10 bg-slate-900/90 py-2.5 pl-9 pr-3 text-xs text-white outline-none focus:border-cyan-400"
                placeholder="Search products by name, category, brand, or SKU..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <span className="text-xs text-slate-400">
              Showing {filteredProducts.length} of {products.length} products
            </span>
          </div>

          <div className="flex flex-wrap gap-2">
            {categories.map(cat => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategoryFilter(cat)}
                className={
                  'rounded-xl border px-3 py-1.5 text-xs font-semibold transition ' +
                  (categoryFilter === cat
                    ? 'border-cyan-300 bg-cyan-400 text-slate-950 font-bold'
                    : 'border-white/10 bg-slate-900 text-slate-300 hover:bg-white/5')
                }
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Product Grid */}
        {loading ? (
          <p className="py-16 text-center text-sm text-slate-400">Loading catalog from Cloudflare...</p>
        ) : filteredProducts.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredProducts.map(p => (
              <article
                key={p.id}
                className="flex flex-col rounded-2xl border border-white/10 bg-slate-900/75 p-4 shadow-xl shadow-black/10 transition hover:border-cyan-400/40"
              >
                <div className="grid aspect-[5/3] place-items-center rounded-xl bg-gradient-to-br from-slate-800 to-slate-950 text-cyan-300">
                  <ShoppingBag size={42} />
                </div>
                <div className="mt-4 flex-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-cyan-300">
                    {p.category || 'USA–Raw Strength'}
                  </p>
                  <h3 className="mt-1 font-bold text-white text-base leading-snug">{p.name}</h3>
                  <p className="mt-1 text-xs text-slate-400">
                    {[p.brand, p.package_type, p.sku && 'SKU ' + p.sku].filter(Boolean).join(' · ') || 'Official product'}
                  </p>
                  <p className="mt-3 text-xl font-extrabold text-white">
                    {money(p.price)} <span className="text-xs font-normal text-slate-500">/ {p.unit || 'PCS'}</span>
                  </p>
                  <p className={`mt-1 text-xs font-medium ${p.available_stock > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {p.available_stock > 0 ? `${p.available_stock} ${p.unit || 'PCS'} in stock` : 'Out of stock'}
                  </p>
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <button
                    className={button + ' flex-1'}
                    disabled={p.available_stock < 1}
                    onClick={() => setQty(p.id, (cart[p.id] || 0) + 1)}
                  >
                    {p.available_stock < 1 ? 'Out of stock' : 'Add to cart'} {p.available_stock >= 1 && <ArrowRight size={15} />}
                  </button>
                  {cart[p.id] > 0 && (
                    <span className="min-w-7 text-center text-sm font-bold text-cyan-200">
                      {cart[p.id]}
                    </span>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-12 text-center">
            <ShoppingBag className="mx-auto text-slate-500" size={38} />
            <h3 className="mt-3 font-bold text-white text-base">No products match your criteria</h3>
            <p className="mt-1 text-sm text-slate-400">
              Try adjusting your search terms or selecting a different category.
            </p>
          </div>
        )}
      </main>

      {/* Cart Drawer */}
      {checkout && (
        <div
          className="fixed inset-0 z-40 flex justify-end bg-black/70 backdrop-blur-sm"
          role="presentation"
          onMouseDown={e => {
            if (e.target === e.currentTarget) setCheckout(false);
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="checkout-title"
            className="h-full w-full max-w-xl overflow-y-auto border-l border-white/10 bg-slate-950 p-5 shadow-2xl sm:p-7"
          >
            <div className="flex items-center justify-between">
              <h2 id="checkout-title" className="text-xl font-bold text-white">Your Cart &amp; Checkout</h2>
              <button
                aria-label="Close cart"
                onClick={() => setCheckout(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-white/10"
              >
                <X />
              </button>
            </div>

            {cartItems.length ? (
              <>
                <div className="mt-5 space-y-3">
                  {cartItems.map(p => (
                    <div key={p.id} className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-slate-900 p-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-white">{p.name}</p>
                        <p className="text-xs text-slate-400">{money(p.price)} each</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          aria-label={'Quantity for ' + p.name}
                          className="w-16 rounded-lg bg-slate-800 px-2 py-2 text-center text-sm text-white border border-white/10"
                          type="number"
                          min="0"
                          max={p.available_stock}
                          value={p.quantity}
                          onChange={e => setQty(p.id, Math.min(p.available_stock, Number(e.target.value)))}
                        />
                        <span className="w-20 text-right text-sm font-semibold text-white">
                          {money(p.price * p.quantity)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex justify-between border-t border-white/10 pt-4 text-lg font-extrabold text-white">
                  <span>Order Total:</span>
                  <span className="text-cyan-300">{money(total)}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  Orders are submitted as verified Cash on Delivery (COD) requests and confirmed by our team.
                </p>

                <form className="mt-6 space-y-3" onSubmit={submit}>
                  <h3 className="font-bold text-white text-base">Delivery Details</h3>
                  <input
                    className={field}
                    placeholder="Full name *"
                    required
                    maxLength="120"
                    value={customer.customer_name}
                    onChange={e => setCustomer({ ...customer, customer_name: e.target.value })}
                  />
                  <input
                    className={field}
                    placeholder="Mobile phone number *"
                    required
                    maxLength="30"
                    value={customer.phone}
                    onChange={e => setCustomer({ ...customer, phone: e.target.value })}
                  />
                  <input
                    className={field}
                    type="email"
                    placeholder="Email address (optional)"
                    value={customer.email}
                    onChange={e => setCustomer({ ...customer, email: e.target.value })}
                  />
                  <textarea
                    className={field + ' min-h-24'}
                    placeholder="Complete delivery address with PIN code *"
                    required
                    maxLength="1000"
                    value={customer.shipping_address}
                    onChange={e => setCustomer({ ...customer, shipping_address: e.target.value })}
                  />
                  <textarea
                    className={field + ' min-h-16'}
                    placeholder="Order notes or instructions (optional)"
                    maxLength="1000"
                    value={customer.customer_note}
                    onChange={e => setCustomer({ ...customer, customer_note: e.target.value })}
                  />
                  <button className={button + ' w-full'} disabled={busy || !cartItems.length}>
                    {busy ? 'Submitting order...' : 'Submit Order Request · ' + money(total)}
                  </button>
                </form>
              </>
            ) : (
              <p className="py-16 text-center text-sm text-slate-400">Your cart is empty. Add a product to continue.</p>
            )}
          </section>
        </div>
      )}

      <footer className="border-t border-white/10 px-4 py-6 text-center text-xs text-slate-500">
        © {new Date().getFullYear()} United Sciences Alliance · Raw Strength Calisthenics. Official Store.
      </footer>
    </div>
  );
}
