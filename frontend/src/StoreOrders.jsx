import React, { useEffect, useMemo, useState } from 'react';
import { ClipboardList, RefreshCw, Search, CheckCircle2, PackageCheck, AlertCircle, ShoppingBag } from 'lucide-react';

const statuses = ['Pending', 'Confirmed', 'Packed', 'Dispatched', 'Delivered', 'Cancelled', 'Returned'];
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value || 0));

export default function StoreOrders({ apiFetch, notify = () => {}, canManage = false }) {
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  const load = async () => {
    if (!canManage) return;
    setBusy(true);
    try {
      const result = await apiFetch('/store/orders');
      setRows(Array.isArray(result) ? result : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    load();
  }, [canManage]);

  const change = async (id, status) => {
    setBusy(true);
    setError('');
    try {
      await apiFetch('/store/orders/' + id, { method: 'PATCH', body: JSON.stringify({ status }) });
      await load();
      notify('Store order ' + id + ' status updated to ' + status + '.');
    } catch (e) {
      setError(e.message);
      notify(e.message);
    } finally {
      setBusy(false);
    }
  };

  const filteredRows = useMemo(() => {
    return rows.filter(order => {
      if (statusFilter !== 'All' && String(order.order_status).toLowerCase() !== statusFilter.toLowerCase()) {
        return false;
      }
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        const haystack = [
          order.order_code,
          order.customer_name,
          order.phone,
          order.email,
          order.shipping_address,
          order.customer_note
        ].filter(Boolean).join(' ').toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [rows, statusFilter, query]);

  const metrics = useMemo(() => {
    const totalCount = rows.length;
    const pendingCount = rows.filter(r => String(r.order_status).toLowerCase() === 'pending').length;
    const confirmedCount = rows.filter(r => ['confirmed', 'packed', 'dispatched'].includes(String(r.order_status).toLowerCase())).length;
    const deliveredCount = rows.filter(r => String(r.order_status).toLowerCase() === 'delivered').length;
    const totalRevenue = rows.reduce((acc, r) => acc + (Number(r.total_amount) || 0), 0);
    return { totalCount, pendingCount, confirmedCount, deliveredCount, totalRevenue };
  }, [rows]);

  if (!canManage) return null;

  return (
    <section className="space-y-4 rounded-2xl border border-cyan-400/20 bg-slate-900/80 p-5 shadow-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-white">
            <ClipboardList className="text-cyan-400" size={20} /> USA–Raw Strength Store Orders
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            Real-time customer orders placed via the online storefront. Orders are captured as COD requests and can be confirmed or updated below.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/#store"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-400/20"
          >
            <ShoppingBag size={14} /> Open Customer Storefront ↗
          </a>
          <button
            type="button"
            disabled={busy}
            onClick={() => load().catch(e => setError(e.message))}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-xs font-semibold text-cyan-200 hover:border-cyan-400/30"
          >
            <RefreshCw size={14} className={busy ? 'animate-spin' : ''} /> Refresh Orders
          </button>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-white/10 bg-slate-950/70 p-3">
          <p className="text-[11px] font-semibold uppercase text-slate-400">Total Store Orders</p>
          <p className="mt-1 text-2xl font-black text-white">{metrics.totalCount}</p>
          <p className="text-[10px] text-slate-500">Gross captured</p>
        </div>
        <div className="rounded-xl border border-amber-400/20 bg-amber-950/20 p-3">
          <p className="text-[11px] font-semibold uppercase text-amber-300">Pending Review</p>
          <p className="mt-1 text-2xl font-black text-amber-200">{metrics.pendingCount}</p>
          <p className="text-[10px] text-slate-500">Awaiting confirmation</p>
        </div>
        <div className="rounded-xl border border-cyan-400/20 bg-cyan-950/20 p-3">
          <p className="text-[11px] font-semibold uppercase text-cyan-300">Processing / In Transit</p>
          <p className="mt-1 text-2xl font-black text-cyan-200">{metrics.confirmedCount}</p>
          <p className="text-[10px] text-slate-500">Confirmed or dispatched</p>
        </div>
        <div className="rounded-xl border border-emerald-400/20 bg-emerald-950/20 p-3">
          <p className="text-[11px] font-semibold uppercase text-emerald-300">Captured Revenue</p>
          <p className="mt-1 text-2xl font-black text-emerald-200">{money(metrics.totalRevenue)}</p>
          <p className="text-[10px] text-slate-500">{metrics.deliveredCount} delivered</p>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-white/10 bg-slate-950/60 p-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="absolute left-3 top-2.5 text-slate-400" size={15} />
          <input
            className="w-full rounded-lg border border-white/10 bg-slate-900 py-2 pl-9 pr-3 text-xs text-white outline-none focus:border-cyan-400"
            placeholder="Search order code, customer name, phone, address..."
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-slate-400">Status:</label>
          <select
            className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white outline-none focus:border-cyan-400"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="All">All Statuses ({rows.length})</option>
            {statuses.map(s => {
              const count = rows.filter(r => String(r.order_status).toLowerCase() === s.toLowerCase()).length;
              return <option key={s} value={s}>{s} ({count})</option>;
            })}
          </select>
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-lg border border-rose-400/30 bg-rose-950/30 p-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      {/* Orders Table */}
      <div className="overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full min-w-[900px] text-left text-xs">
          <thead className="border-b border-white/10 bg-slate-950/90 text-slate-400 uppercase tracking-wider text-[11px]">
            <tr>
              <th className="px-3 py-3">Order Code</th>
              <th className="px-3 py-3">Customer</th>
              <th className="px-3 py-3">Delivery Address</th>
              <th className="px-3 py-3">Items & Quantity</th>
              <th className="px-3 py-3">Total (INR)</th>
              <th className="px-3 py-3">Payment</th>
              <th className="px-3 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 bg-slate-900/40">
            {filteredRows.map(order => (
              <tr key={order.id} className="text-slate-300 transition hover:bg-white/5 align-top">
                <td className="px-3 py-3 whitespace-nowrap">
                  <strong className="block font-bold text-white text-sm">{order.order_code}</strong>
                  <span className="text-[10px] text-slate-500">
                    {String(order.created_at || '').replace('T', ' ').slice(0, 16)}
                  </span>
                  {order.customer_note && (
                    <div className="mt-1 max-w-[180px] rounded bg-white/5 p-1 text-[10px] text-amber-200">
                      Note: {order.customer_note}
                    </div>
                  )}
                </td>
                <td className="px-3 py-3">
                  <p className="font-semibold text-white">{order.customer_name}</p>
                  <p className="text-cyan-300">{order.phone}</p>
                  {order.email && <p className="text-slate-500">{order.email}</p>}
                </td>
                <td className="max-w-64 whitespace-normal px-3 py-3 leading-relaxed text-slate-300">
                  {order.shipping_address}
                </td>
                <td className="px-3 py-3">
                  <div className="space-y-1">
                    {(order.items || []).map(item => (
                      <div key={item.id} className="flex items-center gap-2 text-slate-200">
                        <span className="font-medium">{item.product_name}</span>
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold text-cyan-300">
                          × {item.quantity}
                        </span>
                        <span className="text-slate-500">({money(item.unit_price)})</span>
                      </div>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-3 font-bold text-white text-sm whitespace-nowrap">
                  {money(order.total_amount)}
                </td>
                <td className="px-3 py-3 whitespace-nowrap">
                  <p className="text-slate-300 font-medium">{order.payment_method}</p>
                  <p className="text-[11px] font-semibold text-amber-400">{order.payment_status}</p>
                </td>
                <td className="px-3 py-3 whitespace-nowrap">
                  <select
                    aria-label={'Status for ' + order.order_code}
                    disabled={busy}
                    value={order.order_status}
                    onChange={e => change(order.id, e.target.value)}
                    className="rounded-lg border border-white/20 bg-slate-950 px-2.5 py-1.5 text-xs font-semibold text-white outline-none focus:border-cyan-400"
                  >
                    {statuses.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filteredRows.length && (
          <div className="py-12 text-center text-sm text-slate-500">
            {rows.length === 0 ? 'No customer storefront orders recorded yet.' : 'No orders matched your search or status filter.'}
          </div>
        )}
      </div>
    </section>
  );
}
