import React, { useEffect, useState } from 'react';
import { Activity, ArrowDownUp, Dumbbell, Package, RefreshCw, ShoppingCart, Users, Plus } from 'lucide-react';

const fieldClass = 'w-full min-w-0 rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400';
const buttonClass = 'inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-2 text-sm font-bold text-slate-950 disabled:opacity-50';
const secondaryClass = 'inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm font-semibold text-slate-200 disabled:opacity-50';
const today = () => {
  const d = new Date();
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
};

function InputField({ label, value, onChange, type = 'text', required = false, min, step }) {
  return (
    <label className="block min-w-0 text-xs text-slate-400">
      {label}
      <input
        className={fieldClass + ' mt-1'}
        type={type}
        value={value ?? ''}
        required={required}
        min={min}
        step={step}
        onChange={event => onChange(event.target.value)}
      />
    </label>
  );
}

function SelectField({ label, value, onChange, options }) {
  return (
    <label className="block min-w-0 text-xs text-slate-400">
      {label}
      <select className={fieldClass + ' mt-1'} value={value ?? ''} onChange={event => onChange(event.target.value)}>
        {options.map(option => {
          const item = Array.isArray(option) ? { value: option[0], label: option[1] } : { value: option, label: option };
          return <option key={String(item.value)} value={item.value}>{item.label}</option>;
        })}
      </select>
    </label>
  );
}

function DataTable({ rows = [], columns = [], empty = 'No records found.' }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="min-w-full text-left text-xs text-slate-300">
        <thead className="bg-slate-950 text-[11px] uppercase tracking-wide text-slate-400">
          <tr>{columns.map(column => <th key={column.key} className="whitespace-nowrap px-3 py-3">{column.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length ? rows.map(row => (
            <tr key={row.id} className="border-t border-white/5 hover:bg-white/[0.03]">
              {columns.map(column => (
                <td key={column.key} className="whitespace-nowrap px-3 py-2.5">
                  {column.render ? column.render(row) : (row[column.key] ?? '—')}
                </td>
              ))}
            </tr>
          )) : (
            <tr><td className="px-3 py-6 text-center text-slate-500" colSpan={Math.max(1, columns.length)}>{empty}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function Section({ title, description, children, action }) {
  return (
    <section className="space-y-3 rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-bold text-white">{title}</h3>
          {description && <p className="mt-1 text-xs text-slate-400">{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

const productNumeric = [
  'opening_stock', 'received_qty', 'reserved_qty', 'dispatched_qty', 'free_qty',
  'returned_qty', 'damaged_qty', 'expired_qty', 'quarantined_qty',
  'purchase_cost', 'selling_price', 'reorder_level'
];

export default function BusinessTracking({ apiFetch, employees = [], notify = () => {} }) {
  const [tab, setTab] = useState('overview');
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState('');
  const [data, setData] = useState({
    overview: {}, products: [], services: [], orders: [], members: [], activities: [], ledger: []
  });
  const [product, setProduct] = useState({
    name: '', sku: '', category: 'equipment', brand: '', package_type: '', base_unit: 'PCS',
    opening_stock: '0', received_qty: '0', reserved_qty: '0', dispatched_qty: '0',
    free_qty: '0', returned_qty: '0', damaged_qty: '0', expired_qty: '0',
    quarantined_qty: '0', purchase_cost: '0', selling_price: '0', reorder_level: '0',
    batch_number: '', expiry_date: '', storage_location: ''
  });
  const [movement, setMovement] = useState({
    product_id: '', txn_type: 'receive', quantity: '1', unit: 'PCS', reference: '', notes: ''
  });
  const [order, setOrder] = useState({
    order_code: '', order_date: today(), customer_name: '', contact: '', channel: 'gym counter',
    payment_mode: 'UPI', status: 'Pending', discount: '0', order_value: '0',
    invoice_number: '', shipment_id: '', assigned_employee_id: '', notes: ''
  });
  const [service, setService] = useState({
    name: '', category: 'Training', description: '', training_mode: 'Offline',
    service_unit: 'Session', session_duration: '60', num_sessions: '1',
    plan_validity: '30', standard_price: '0', active: '1'
  });
  const [member, setMember] = useState({
    full_name: '', phone: '', service_id: '', training_mode: 'Offline',
    registration_date: today(), start_date: today(), end_date: '',
    sessions_purchased: '0', sessions_completed: '0', assigned_trainer_id: '',
    status: 'Active', payment_status: 'Pending', invoice_ref: '', notes: ''
  });
  const [activity, setActivity] = useState({
    employee_id: '', related_order_id: '', related_service_id: '', task_type: 'Picking',
    product_id: '', quantity: '0', unit: '', start_time: '', completion_time: '',
    task_status: 'Pending', proof_ref: '', remarks: ''
  });

  const load = async () => {
    const [overview, products, services, orders, members, activities, ledger] = await Promise.all([
      apiFetch('/business/overview'),
      apiFetch('/business/products'),
      apiFetch('/business/services'),
      apiFetch('/business/orders'),
      apiFetch('/business/members'),
      apiFetch('/business/activities'),
      apiFetch('/business/stock-ledger')
    ]);
    setData({ overview, products, services, orders, members, activities, ledger });
    if (!movement.product_id && products.length) setMovement(current => ({ ...current, product_id: String(products[0].id) }));
  };

  useEffect(() => {
    load().catch(error => notify(error.message));
  }, []);

  const perform = async (path, payload, method = 'POST', reset = null) => {
    setBusy(true);
    try {
      await apiFetch(path, { method, body: JSON.stringify(payload) });
      if (reset) reset();
      await load();
      notify('Business record saved successfully.');
    } catch (error) {
      notify(error.message);
    } finally {
      setBusy(false);
    }
  };

  const updateForm = (setter, key, value) => setter(current => ({ ...current, [key]: value }));
  const renderFields = (values, setter, fields) => fields.map(([key, label, type = 'text']) => (
    <InputField
      key={key}
      label={label}
      type={type}
      value={values[key]}
      required={key === 'name' || key === 'full_name'}
      min={type === 'number' ? '0' : undefined}
      step={type === 'number' ? 'any' : undefined}
      onChange={value => updateForm(setter, key, value)}
    />
  ));
  const filterRows = (rows, keys) => rows.filter(row =>
    keys.some(key => String(row[key] ?? '').toLowerCase().includes(search.trim().toLowerCase()))
  );
  const statusOptions = ['Pending', 'Confirmed', 'Packed', 'Dispatched', 'Delivered', 'Completed', 'Cancelled', 'Returned'];
  const activityStatuses = ['Pending', 'In Progress', 'Completed', 'Blocked', 'Cancelled'];

  const saveProduct = event => {
    event.preventDefault();
    const numeric = Object.fromEntries(productNumeric.map(key => [key, Number(product[key] || 0)]));
    if (productNumeric.some(key => !Number.isFinite(numeric[key]) || numeric[key] < 0)) {
      notify('Product quantities and prices must be finite non-negative numbers.');
      return;
    }
    perform('/business/products', { ...product, ...numeric }, 'POST', () => setProduct({
      name: '', sku: '', category: 'equipment', brand: '', package_type: '', base_unit: 'PCS',
      opening_stock: '0', received_qty: '0', reserved_qty: '0', dispatched_qty: '0',
      free_qty: '0', returned_qty: '0', damaged_qty: '0', expired_qty: '0',
      quarantined_qty: '0', purchase_cost: '0', selling_price: '0', reorder_level: '0',
      batch_number: '', expiry_date: '', storage_location: ''
    }));
  };

  const saveMovement = event => {
    event.preventDefault();
    perform('/business/stock-ledger', {
      ...movement, product_id: Number(movement.product_id), quantity: Number(movement.quantity)
    }, 'POST', () => setMovement(current => ({ ...current, quantity: '1', reference: '', notes: '' })));
  };

  const saveOrder = event => {
    event.preventDefault();
    perform('/business/orders', {
      ...order,
      order_value: Number(order.order_value || 0),
      discount: Number(order.discount || 0),
      assigned_employee_id: order.assigned_employee_id ? Number(order.assigned_employee_id) : null
    }, 'POST', () => setOrder({
      order_code: '', order_date: today(), customer_name: '', contact: '', channel: 'gym counter',
      payment_mode: 'UPI', status: 'Pending', discount: '0', order_value: '0',
      invoice_number: '', shipment_id: '', assigned_employee_id: '', notes: ''
    }));
  };

  const saveService = event => {
    event.preventDefault();
    perform('/business/services', {
      ...service, session_duration: Number(service.session_duration || 0),
      num_sessions: Number(service.num_sessions || 0), plan_validity: Number(service.plan_validity || 0),
      standard_price: Number(service.standard_price || 0), active: Number(service.active)
    }, 'POST', () => setService({
      name: '', category: 'Training', description: '', training_mode: 'Offline',
      service_unit: 'Session', session_duration: '60', num_sessions: '1',
      plan_validity: '30', standard_price: '0', active: '1'
    }));
  };

  const saveMember = event => {
    event.preventDefault();
    perform('/business/members', {
      ...member,
      service_id: member.service_id ? Number(member.service_id) : null,
      assigned_trainer_id: member.assigned_trainer_id ? Number(member.assigned_trainer_id) : null,
      sessions_purchased: Number(member.sessions_purchased || 0),
      sessions_completed: Number(member.sessions_completed || 0)
    }, 'POST', () => setMember({
      full_name: '', phone: '', service_id: '', training_mode: 'Offline',
      registration_date: today(), start_date: today(), end_date: '',
      sessions_purchased: '0', sessions_completed: '0', assigned_trainer_id: '',
      status: 'Active', payment_status: 'Pending', invoice_ref: '', notes: ''
    }));
  };

  const saveActivity = event => {
    event.preventDefault();
    perform('/business/activities', {
      ...activity,
      employee_id: Number(activity.employee_id),
      related_order_id: activity.related_order_id ? Number(activity.related_order_id) : null,
      related_service_id: activity.related_service_id ? Number(activity.related_service_id) : null,
      product_id: activity.product_id ? Number(activity.product_id) : null,
      quantity: Number(activity.quantity || 0)
    }, 'POST', () => setActivity({
      employee_id: '', related_order_id: '', related_service_id: '', task_type: 'Picking',
      product_id: '', quantity: '0', unit: '', start_time: '', completion_time: '',
      task_status: 'Pending', proof_ref: '', remarks: ''
    }));
  };

  const setOrderStatus = (row, status) => perform('/business/orders/' + row.id, { status }, 'PATCH');
  const setMemberStatus = (row, status) => perform('/business/members/' + row.id, { status }, 'PATCH');
  const setActivityStatus = (row, task_status) => perform('/business/activities/' + row.id, { task_status }, 'PATCH');
  const recordSession = row => perform('/business/members/' + row.id, {
    sessions_completed: Number(row.sessions_completed || 0) + 1
  }, 'PATCH');

  const tabs = [
    ['overview', 'Dashboard', Activity],
    ['products', 'Products & Inventory', Package],
    ['orders', 'Orders', ShoppingCart],
    ['services', 'Services & Members', Dumbbell],
    ['activities', 'Employee Activities', Users]
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-white">Business Tracking</h2>
          <p className="mt-1 text-xs text-slate-400">Products, stock ledger, orders, services, memberships and employee activities.</p>
        </div>
        <button type="button" className={secondaryClass} onClick={() => load().catch(error => notify(error.message))} disabled={busy}>
          <RefreshCw size={15}/> Refresh all
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map(([key, label, Icon]) => (
          <button key={key} type="button" onClick={() => { setTab(key); setSearch(''); }}
            className={'inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold ' +
              (tab === key ? 'border-cyan-300 bg-cyan-400 text-slate-950' : 'border-white/10 bg-slate-900 text-slate-300')}>
            <Icon size={15}/>{label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ['Products', data.overview.products, 'Catalog items'],
            ['Low stock', data.overview.low_stock, 'At or below reorder level'],
            ['Orders', data.overview.orders, 'All order records'],
            ['Open orders', data.overview.open_orders, 'Awaiting completion'],
            ['Services', data.overview.services, 'Training plans'],
            ['Active members', data.overview.active_members, 'Current memberships'],
            ['Activities', data.overview.activities, 'Employee activity records'],
            ['Completed activities', data.overview.completed_activities, 'Verified as completed']
          ].map(([label, value, hint]) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-slate-900/65 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
              <p className="mt-2 text-3xl font-extrabold text-cyan-300">{value ?? 0}</p>
              <p className="mt-1 text-xs text-slate-500">{hint}</p>
            </div>
          ))}
          <div className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 sm:col-span-2 xl:col-span-4">
            <p className="text-sm font-semibold text-white">Business data overview</p>
            <p className="mt-1 text-xs text-slate-400">{data.products.length} products · {data.orders.length} orders · {data.services.length} services · {data.members.length} memberships · {data.activities.length} activities · {data.ledger.length} stock movements</p>
          </div>
        </div>
      )}

      {tab === 'products' && (
        <div className="space-y-4">
          <Section title="Add product / inventory item" description="Captures the complete product master and stock quantities used by the desktop inventory calculation.">
            <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={saveProduct}>
              {renderFields(product, setProduct, [
                ['name', 'Product name'], ['sku', 'SKU'], ['category', 'Category'],
                ['brand', 'Brand'], ['package_type', 'Package type'], ['base_unit', 'Weight / stock unit'],
                ['opening_stock', 'Opening stock', 'number'], ['received_qty', 'Received quantity', 'number'],
                ['reserved_qty', 'Reserved quantity', 'number'], ['dispatched_qty', 'Sold / dispatched quantity', 'number'],
                ['free_qty', 'Free / promotional quantity', 'number'], ['returned_qty', 'Returned quantity', 'number'],
                ['damaged_qty', 'Damaged quantity', 'number'], ['expired_qty', 'Expired quantity', 'number'],
                ['quarantined_qty', 'Quarantined quantity', 'number'], ['purchase_cost', 'Purchase cost', 'number'],
                ['selling_price', 'Selling price', 'number'], ['reorder_level', 'Reorder level', 'number'],
                ['batch_number', 'Batch number'], ['expiry_date', 'Expiry date', 'date'],
                ['storage_location', 'Storage location']
              ])}
              <div className="flex items-end"><button className={buttonClass} disabled={busy}><Plus size={15}/> Add product</button></div>
            </form>
          </Section>
          <Section title="Record stock movement" description="Each movement is stored in the stock ledger and updates the matching aggregate quantity atomically.">
            <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6" onSubmit={saveMovement}>
              <SelectField label="Product" value={movement.product_id} onChange={value => updateForm(setMovement, 'product_id', value)}
                options={data.products.map(row => [String(row.id), (row.sku ? row.sku + ' · ' : '') + row.name])}/>
              <SelectField label="Movement type" value={movement.txn_type} onChange={value => updateForm(setMovement, 'txn_type', value)}
                options={['receive', 'reserve', 'release', 'dispatch', 'free', 'return', 'damage', 'expire', 'quarantine', 'unquarantine']}/>
              <InputField label="Quantity" type="number" min="0.0001" step="any" value={movement.quantity} onChange={value => updateForm(setMovement, 'quantity', value)}/>
              <InputField label="Unit" value={movement.unit} onChange={value => updateForm(setMovement, 'unit', value)}/>
              <InputField label="Reference" value={movement.reference} onChange={value => updateForm(setMovement, 'reference', value)}/>
              <InputField label="Notes" value={movement.notes} onChange={value => updateForm(setMovement, 'notes', value)}/>
              <div className="sm:col-span-2 xl:col-span-6"><button className={buttonClass} disabled={busy || !data.products.length}><ArrowDownUp size={15}/> Save stock movement</button></div>
            </form>
          </Section>
          <Section title="Product inventory" description="Available stock is calculated with the same opening, received, reserved, dispatched, free, returned, damaged, expired and quarantine fields as the desktop.">
            <input className={fieldClass + ' mb-3'} value={search} onChange={event => setSearch(event.target.value)} placeholder="Search product, SKU, brand, batch or location"/>
            <DataTable rows={filterRows(data.products, ['name', 'sku', 'category', 'brand', 'batch_number', 'storage_location'])} columns={[
              {key:'sku',label:'SKU'},{key:'name',label:'Product'},{key:'category',label:'Category'},
              {key:'brand',label:'Brand'},{key:'package_type',label:'Package'},{key:'base_unit',label:'Unit'},
              {key:'opening_stock',label:'Opening'},{key:'received_qty',label:'Received'},
              {key:'reserved_qty',label:'Reserved'},{key:'dispatched_qty',label:'Dispatched'},
              {key:'free_qty',label:'Free'},{key:'returned_qty',label:'Returned'},
              {key:'damaged_qty',label:'Damaged'},{key:'expired_qty',label:'Expired'},
              {key:'quarantined_qty',label:'Quarantined'},
              {key:'available_stock',label:'Available',render:row=><b className="text-cyan-300">{Number(row.available_stock || 0).toFixed(2)}</b>},
              {key:'reorder_level',label:'Reorder'},{key:'purchase_cost',label:'Cost'},
              {key:'selling_price',label:'Price'},{key:'batch_number',label:'Batch'},
              {key:'expiry_date',label:'Expiry'},{key:'storage_location',label:'Location'}
            ]}/>
          </Section>
          <Section title="Stock movement history">
            <DataTable rows={filterRows(data.ledger, ['product_name', 'sku', 'txn_type', 'reference', 'notes'])} columns={[
              {key:'created_at',label:'Date'},{key:'product_name',label:'Product'},{key:'sku',label:'SKU'},
              {key:'txn_type',label:'Movement'},{key:'quantity',label:'Quantity'},{key:'unit',label:'Unit'},
              {key:'reference',label:'Reference'},{key:'notes',label:'Notes'},{key:'created_by',label:'Recorded by'}
            ]}/>
          </Section>
        </div>
      )}

      {tab === 'orders' && (
        <div className="space-y-4">
          <Section title="Create order / sale" description="Records order identity, channel, customer, payment, invoice, shipment, assigned employee and financial values.">
            <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={saveOrder}>
              {renderFields(order, setOrder, [
                ['order_code', 'External order ID'], ['order_date', 'Order date', 'date'],
                ['customer_name', 'Customer name'], ['contact', 'Contact'],
                ['discount', 'Discount', 'number'], ['order_value', 'Order value', 'number'],
                ['invoice_number', 'Invoice number'], ['shipment_id', 'Shipment ID'], ['notes', 'Remarks']
              ])}
              <SelectField label="Sales channel" value={order.channel} onChange={value => updateForm(setOrder, 'channel', value)}
                options={['Amazon', 'Flipkart', 'website', 'WhatsApp', 'gym counter', 'other']}/>
              <SelectField label="Payment mode" value={order.payment_mode} onChange={value => updateForm(setOrder, 'payment_mode', value)}
                options={['UPI', 'Cash', 'Card', 'Bank transfer', 'COD', 'Other']}/>
              <SelectField label="Order status" value={order.status} onChange={value => updateForm(setOrder, 'status', value)} options={statusOptions}/>
              <SelectField label="Assigned employee" value={order.assigned_employee_id} onChange={value => updateForm(setOrder, 'assigned_employee_id', value)}
                options={[['', 'Unassigned'], ...employees.map(row => [String(row.id), row.name])]}/>
              <div className="flex items-end"><button className={buttonClass} disabled={busy}><Plus size={15}/> Add order</button></div>
            </form>
          </Section>
          <Section title="Order tracking">
            <input className={fieldClass + ' mb-3'} value={search} onChange={event => setSearch(event.target.value)} placeholder="Search order, customer, invoice or shipment"/>
            <DataTable rows={filterRows(data.orders, ['order_code', 'customer_name', 'contact', 'invoice_number', 'shipment_id', 'channel'])} columns={[
              {key:'order_code',label:'Order ID'},{key:'order_date',label:'Date'},{key:'customer_name',label:'Customer'},
              {key:'contact',label:'Contact'},{key:'channel',label:'Channel'},{key:'payment_mode',label:'Payment'},
              {key:'discount',label:'Discount'},{key:'order_value',label:'Value'},{key:'invoice_number',label:'Invoice'},
              {key:'shipment_id',label:'Shipment'},
              {key:'status',label:'Status',render:row=><select className={fieldClass} value={row.status || 'Pending'} onChange={event => setOrderStatus(row, event.target.value)}>{statusOptions.map(value=><option key={value}>{value}</option>)}</select>},
              {key:'assigned_employee_id',label:'Employee'},{key:'remarks',label:'Remarks'}
            ]}/>
          </Section>
        </div>
      )}

      {tab === 'services' && (
        <div className="space-y-4">
          <Section title="Services and training plans" description="Supports offline, online and hybrid services with session duration, plan validity and pricing.">
            <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={saveService}>
              {renderFields(service, setService, [
                ['name', 'Service name'], ['category', 'Category'], ['description', 'Description'],
                ['session_duration', 'Session duration (minutes)', 'number'], ['num_sessions', 'Sessions per plan', 'number'],
                ['plan_validity', 'Plan validity (days)', 'number'], ['standard_price', 'Standard price', 'number']
              ])}
              <SelectField label="Training mode" value={service.training_mode} onChange={value => updateForm(setService, 'training_mode', value)} options={['Offline', 'Online', 'Hybrid']}/>
              <SelectField label="Service unit" value={service.service_unit} onChange={value => updateForm(setService, 'service_unit', value)} options={['Session', 'Month', 'Program', 'Hour']}/>
              <SelectField label="Active" value={service.active} onChange={value => updateForm(setService, 'active', value)} options={[['1','Yes'],['0','No']]}/>
              <div className="flex items-end"><button className={buttonClass} disabled={busy}><Plus size={15}/> Add service</button></div>
            </form>
            <DataTable rows={data.services} columns={[
              {key:'id',label:'ID'},{key:'name',label:'Service'},{key:'category',label:'Category'},
              {key:'description',label:'Description'},{key:'training_mode',label:'Mode'},
              {key:'service_unit',label:'Unit'},{key:'session_duration',label:'Minutes'},
              {key:'num_sessions',label:'Sessions'},{key:'plan_validity',label:'Validity days'},
              {key:'standard_price',label:'Price'},{key:'active',label:'Active',render:row=>Number(row.active) ? 'Yes' : 'No'}
            ]}/>
          </Section>
          <Section title="Register member / membership" description="Tracks service, trainer, registration dates, purchased/completed sessions, status, payment and invoice reference.">
            <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={saveMember}>
              {renderFields(member, setMember, [
                ['full_name', 'Member name'], ['phone', 'Contact / phone'],
                ['registration_date', 'Registration date', 'date'], ['start_date', 'Start date', 'date'],
                ['end_date', 'Expiry date', 'date'], ['sessions_purchased', 'Sessions purchased', 'number'],
                ['sessions_completed', 'Sessions completed', 'number'], ['invoice_ref', 'Invoice reference'],
                ['notes', 'Remarks']
              ])}
              <SelectField label="Service / plan" value={member.service_id} onChange={value => updateForm(setMember, 'service_id', value)}
                options={[['', 'Select service'], ...data.services.map(row => [String(row.id), row.name])]}/>
              <SelectField label="Training mode" value={member.training_mode} onChange={value => updateForm(setMember, 'training_mode', value)} options={['Offline', 'Online', 'Hybrid']}/>
              <SelectField label="Assigned trainer" value={member.assigned_trainer_id} onChange={value => updateForm(setMember, 'assigned_trainer_id', value)}
                options={[['', 'Unassigned'], ...employees.map(row => [String(row.id), row.name])]}/>
              <SelectField label="Membership status" value={member.status} onChange={value => updateForm(setMember, 'status', value)} options={['Active', 'Expired', 'Inactive', 'Cancelled', 'Suspended']}/>
              <SelectField label="Payment status" value={member.payment_status} onChange={value => updateForm(setMember, 'payment_status', value)} options={['Pending', 'Paid', 'Partial', 'Overdue', 'Refunded']}/>
              <div className="flex items-end"><button className={buttonClass} disabled={busy}><Plus size={15}/> Add member</button></div>
            </form>
          </Section>
          <Section title="Memberships and sessions">
            <DataTable rows={filterRows(data.members, ['full_name', 'phone', 'plan_name', 'status', 'payment_status', 'invoice_ref'])} columns={[
              {key:'full_name',label:'Member'},{key:'phone',label:'Contact'},{key:'plan_name',label:'Service'},
              {key:'training_mode',label:'Mode'},{key:'registration_date',label:'Registered'},
              {key:'start_date',label:'Start'},{key:'end_date',label:'Expiry'},
              {key:'sessions_purchased',label:'Purchased'},{key:'sessions_completed',label:'Completed'},
              {key:'sessions_left',label:'Sessions left',render:row=>Math.max(0,Number(row.sessions_purchased||0)-Number(row.sessions_completed||0))},
              {key:'status',label:'Status',render:row=><select className={fieldClass} value={row.status || 'Active'} onChange={event => setMemberStatus(row,event.target.value)}>{['Active','Expired','Inactive','Cancelled','Suspended'].map(value=><option key={value}>{value}</option>)}</select>},
              {key:'payment_status',label:'Payment'},{key:'invoice_ref',label:'Invoice'},
              {key:'session_action',label:'Action',render:row=><button className={secondaryClass} onClick={()=>recordSession(row)} disabled={busy}>Record session</button>}
            ]}/>
          </Section>
        </div>
      )}

      {tab === 'activities' && (
        <div className="space-y-4">
          <Section title="Assign employee activity" description="Records operational and training work with linked order, service, product, quantity, proof and remarks.">
            <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={saveActivity}>
              <SelectField label="Employee" value={activity.employee_id} onChange={value => updateForm(setActivity, 'employee_id', value)}
                options={[['', 'Select employee'], ...employees.map(row => [String(row.id), row.name])]}/>
              <SelectField label="Activity type" value={activity.task_type} onChange={value => updateForm(setActivity, 'task_type', value)}
                options={['Picking', 'Packing', 'QC', 'Dispatch', 'Training', 'Attendance', 'other']}/>
              <SelectField label="Related order" value={activity.related_order_id} onChange={value => updateForm(setActivity, 'related_order_id', value)}
                options={[['', 'No order'], ...data.orders.map(row => [String(row.id), row.order_code || ('Order #' + row.id)])]}/>
              <SelectField label="Related service" value={activity.related_service_id} onChange={value => updateForm(setActivity, 'related_service_id', value)}
                options={[['', 'No service'], ...data.services.map(row => [String(row.id), row.name])]}/>
              <SelectField label="Product" value={activity.product_id} onChange={value => updateForm(setActivity, 'product_id', value)}
                options={[['', 'No product'], ...data.products.map(row => [String(row.id), row.name])]}/>
              {renderFields(activity, setActivity, [
                ['quantity', 'Quantity', 'number'], ['unit', 'Unit'],
                ['start_time', 'Start time', 'datetime-local'], ['completion_time', 'Completion time', 'datetime-local'],
                ['proof_ref', 'Proof / evidence URL'], ['remarks', 'Remarks']
              ])}
              <SelectField label="Activity status" value={activity.task_status} onChange={value => updateForm(setActivity, 'task_status', value)} options={activityStatuses}/>
              <div className="flex items-end"><button className={buttonClass} disabled={busy || !employees.length}><Plus size={15}/> Add activity</button></div>
            </form>
          </Section>
          <Section title="Employee activity tracking">
            <input className={fieldClass + ' mb-3'} value={search} onChange={event => setSearch(event.target.value)} placeholder="Search employee, task, linked order, product or remarks"/>
            <DataTable rows={filterRows(data.activities, ['employee_name', 'task_type', 'order_code', 'service_name', 'product_name', 'remarks', 'proof_ref'])} columns={[
              {key:'id',label:'ID'},{key:'employee_name',label:'Employee'},{key:'task_type',label:'Activity'},
              {key:'order_code',label:'Order'},{key:'service_name',label:'Service'},{key:'product_name',label:'Product'},
              {key:'quantity',label:'Quantity'},{key:'unit',label:'Unit'},{key:'start_time',label:'Start'},
              {key:'completion_time',label:'Completed'},{key:'proof_ref',label:'Proof'},
              {key:'task_status',label:'Status',render:row=><select className={fieldClass} value={row.task_status || 'Pending'} onChange={event => setActivityStatus(row,event.target.value)}>{activityStatuses.map(value=><option key={value}>{value}</option>)}</select>},
              {key:'verified_by',label:'Verified by'},{key:'remarks',label:'Remarks'}
            ]}/>
          </Section>
        </div>
      )}
    </div>
  );
}
