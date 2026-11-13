import React, { useEffect, useMemo, useState } from 'react';
import brandLogo from '../../assets/raw_strength_brand.png';
import {
  ArrowLeft, ArrowRight, CheckCircle2, Search, ShoppingBag, ShoppingCart, Store, X,
  ShieldCheck, Truck, RotateCcw, CreditCard, Star, Filter, Sparkles, Plus, Minus,
  Trash2, QrCode, Package, Clock, MapPin, Phone, Mail, FileText, ChevronDown, ChevronUp,
  ExternalLink, Check, Tag, Info, Percent, Award, Copy, Printer
} from 'lucide-react';

const api = async (path, options = {}) => {
  const response = await fetch('/api' + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.error || 'Request failed (' + response.status + ')');
  return data;
};

const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value || 0));

const FLAGSHIP_CATALOG = [
  {
    id: 101,
    sku: 'USA-RS-RNG32',
    name: 'USA Raw Strength Olympic Birch Gymnastic Rings (32mm)',
    category: 'Rings & Straps',
    brand: 'USA Raw Strength',
    package_type: 'Complete Set (Rings, Straps & Storage Bag)',
    unit: 'SET',
    price: 2499,
    original_price: 3499,
    rating: 4.9,
    reviews_count: 148,
    badge: 'Bestseller',
    available_stock: 45,
    tagline: 'Competition-grade 32mm Baltic birch wood with 15ft heavy-duty straps',
    description: 'Precision-turned competition 32mm textured Baltic birch wood rings paired with 15ft heavy-duty nylon straps, numbered measurement markings, and solid alloy steel cam buckles tested up to 450 kg.',
    specs: [
      { label: 'Ring Grip Diameter', value: '32mm (Olympic FIG Standard)' },
      { label: 'Strap Dimensions', value: '15 ft (4.5m) length x 1.5 in (38mm) width' },
      { label: 'Buckle Material', value: 'Alloy Steel Zinc-Plated Heavy-Duty Cam Buckle' },
      { label: 'Maximum Breaking Load', value: '450 kg (990 lbs) certified load' },
      { label: 'Wood Finishing', value: 'Natural smooth-sanded Birch, non-slip porous grain' }
    ],
    athlete_quote: 'The 32mm Birch rings have the best natural grip texture for false grip muscle-ups and iron crosses.'
  },
  {
    id: 102,
    sku: 'USA-RS-BELT01',
    name: 'USA Raw Strength Heavy-Duty Weighted Dip Belt',
    category: 'Weights & Belts',
    brand: 'USA Raw Strength',
    package_type: 'Belt with 36" Stainless Steel Chain',
    unit: 'PCS',
    price: 1799,
    original_price: 2499,
    rating: 4.8,
    reviews_count: 94,
    badge: 'Athlete Favorite',
    available_stock: 35,
    tagline: 'Ergonomically contoured neoprene with 36-inch industrial steel chain',
    description: 'Designed for heavy weighted pull-ups, muscle-ups, and dips. Features 6-inch wide reinforced neoprene lumbar cushioning and 36-inch stainless steel chain with heavy-duty alloy screw-lock carabiners.',
    specs: [
      { label: 'Chain Length', value: '36 inches (91 cm) industrial link chain' },
      { label: 'Back Padding', value: '6-inch wide heavy-density contour neoprene' },
      { label: 'Carabiners', value: 'Dual Screw-Lock Alloy Steel Carabiners' },
      { label: 'Maximum Load', value: '200 kg (440 lbs) tested working weight' }
    ],
    athlete_quote: 'Zero hip pinch even with 70kg strapped on dips. Essential for progressive overload in street workout.'
  },
  {
    id: 103,
    sku: 'USA-RS-PARAL',
    name: 'Pro Beech Wood Low Parallettes (Push-Up Bars)',
    category: 'Parallettes & Bars',
    brand: 'USA Raw Strength',
    package_type: 'Pair in Protective Box',
    unit: 'PAIR',
    price: 2899,
    original_price: 3899,
    rating: 4.9,
    reviews_count: 112,
    badge: 'Top Rated',
    available_stock: 20,
    tagline: 'Solid beech wood 38mm ergonomic bars on laser-cut steel base',
    description: 'Ergonomic 38mm solid European beech wood bars fitted on heavy 4mm laser-cut powder-coated steel bases with non-slip silicone pads. Prevents wrist hyperextension during planches, L-sits, and handstands.',
    specs: [
      { label: 'Grip Diameter', value: '38mm ergonomically contoured solid beech' },
      { label: 'Base Construction', value: '4mm laser-cut heavy carbon steel' },
      { label: 'Dimensions', value: 'Length: 40cm | Height: 15cm | Base Width: 20cm' },
      { label: 'Weight Capacity', value: '300 kg (660 lbs) static load' }
    ],
    athlete_quote: 'The 38mm grip feels perfect in the palm. No wrist fatigue during planche and handstand push-up progressions.'
  },
  {
    id: 104,
    sku: 'USA-RS-WHEY2K',
    name: 'USA Raw Strength 100% Whey Isolate (2kg / 4.4 lbs)',
    category: 'Nutrition & Supplements',
    brand: 'USA Raw Strength',
    package_type: 'Jar (Gourmet Belgian Chocolate)',
    unit: 'JAR',
    price: 4299,
    original_price: 5499,
    rating: 4.9,
    reviews_count: 230,
    badge: 'Pure Lab Tested',
    available_stock: 50,
    tagline: 'Cross-flow micro-filtered whey isolate delivering 27g protein per scoop',
    description: 'Ultra-pure 100% whey protein isolate with 27g protein, 6.2g naturally occurring BCAAs, and zero added sugars per serving. Digested rapidly with zero bloating. Informed-Choice batch tested.',
    specs: [
      { label: 'Net Weight', value: '2.0 kg (4.4 lbs) / 66 Servings' },
      { label: 'Protein per Serving', value: '27 grams (Pure CFM Whey Isolate)' },
      { label: 'BCAAs & EAAs', value: '6.2g BCAAs | 13.1g Essential Amino Acids' },
      { label: 'Carbs & Sugar', value: '< 1g Carbs | 0g Added Sugars' },
      { label: 'Quality Certification', value: 'Informed-Choice & FSSAI Certified' }
    ],
    athlete_quote: 'Mixes instantly with cold water, tastes incredible, and keeps recovery on point during high-volume sessions.'
  },
  {
    id: 105,
    sku: 'USA-RS-CREA25',
    name: 'Micronized Creatine Monohydrate (250g Creapure® Grade)',
    category: 'Nutrition & Supplements',
    brand: 'USA Raw Strength',
    package_type: 'Tub (100% Pure Unflavored)',
    unit: 'TUB',
    price: 1099,
    original_price: 1499,
    rating: 5.0,
    reviews_count: 310,
    badge: 'Bestseller',
    available_stock: 80,
    tagline: '200-mesh ultra-micronized creatine for explosive power output',
    description: 'Pharmaceutical-grade 200-mesh micronized creatine monohydrate. Dissolves completely without gritty sediment. Replenishes cellular ATP stores for maximal explosive power, sprint speed, and muscular endurance.',
    specs: [
      { label: 'Net Weight', value: '250 grams / 83 Servings' },
      { label: 'Serving Size', value: '3g (1 level scoop included)' },
      { label: 'Purity Standard', value: '99.9% Ultra-pure Creapure grade' },
      { label: 'Solubility', value: 'Instant 200-mesh micro-particle suspension' }
    ],
    athlete_quote: 'Noticeable boost in repetition endurance and explosive pulling strength within 10 days.'
  },
  {
    id: 106,
    sku: 'USA-RS-CHLK25',
    name: 'Pure Magnesium Carbonate Liquid Chalk (250ml)',
    category: 'Chalk & Accessories',
    brand: 'USA Raw Strength',
    package_type: 'Quick-Dry Squeeze Bottle (250ml)',
    unit: 'BOTTLE',
    price: 649,
    original_price: 899,
    rating: 4.7,
    reviews_count: 88,
    badge: 'Zero Mess',
    available_stock: 120,
    tagline: 'Fast-drying friction amplifier with zero dust clouds and antimicrobial base',
    description: 'High-purity magnesium carbonate in an antimicrobial ethanol suspension. Dries in 12 seconds to leave a moisture-resistant chalk barrier that lasts through grueling ring muscle-up and bar sets.',
    specs: [
      { label: 'Volume', value: '250 ml (Approx. 150 applications)' },
      { label: 'Drying Speed', value: 'Under 15 seconds' },
      { label: 'Residue', value: 'No chalk dust clouds, gym-friendly formulation' },
      { label: 'Skin Feel', value: 'Non-tacky, long-lasting moisture barrier' }
    ],
    athlete_quote: 'A single dime-sized drop lasts through a full 1-hour bar and ring workout with bone-dry grip.'
  },
  {
    id: 107,
    sku: 'USA-RS-BND5PK',
    name: 'Progressive Calisthenics Resistance Bands (Set of 5)',
    category: 'Rings & Straps',
    brand: 'USA Raw Strength',
    package_type: '5-Band Bundle with Carry Pouch',
    unit: 'SET',
    price: 1899,
    original_price: 2799,
    rating: 4.8,
    reviews_count: 165,
    badge: 'Value Bundle',
    available_stock: 60,
    tagline: '100% natural Malaysian latex covering 15 lbs to 175 lbs resistance',
    description: 'Continuous layered natural latex bands designed for assisted pull-ups, front levers, planches, and shoulder mobility drills. High snap resistance with uniform progressive elasticity.',
    specs: [
      { label: 'Bands Included', value: 'Red (15-35 lbs), Black (25-65 lbs), Purple (35-85 lbs), Green (50-125 lbs), Blue (65-175 lbs)' },
      { label: 'Circumference', value: '208 cm (continuous seamless loop)' },
      { label: 'Material', value: '100% Eco-friendly layered Malaysian natural latex' }
    ],
    athlete_quote: 'Essential for breaking through front lever and one-arm pull-up plateaus with scalable assistance.'
  },
  {
    id: 108,
    sku: 'USA-RS-VEST20',
    name: 'Adjustable Tactical Weighted Vest (20kg Heavy Duty)',
    category: 'Weights & Belts',
    brand: 'USA Raw Strength',
    package_type: 'Vest with 20x 1kg Solid Cast Iron Weights',
    unit: 'PCS',
    price: 5499,
    original_price: 7499,
    rating: 4.9,
    reviews_count: 76,
    badge: 'Pro Grade',
    available_stock: 15,
    tagline: '1000D Cordura nylon with 20 individual removable 1kg cast iron ingots',
    description: 'Compact military-spec 1000D Cordura weighted vest. Contoured high-cut chest profile allows full range of motion for deep handstand push-ups, muscle-ups, sprints, and Murph workouts without shifting or bouncing.',
    specs: [
      { label: 'Total Weight', value: '20 kg (Adjustable from 1kg to 20kg)' },
      { label: 'Weight Modules', value: '20x 1kg rust-proof solid cast iron blocks' },
      { label: 'Fabric', value: 'Heavy-duty water-repellent 1000D Cordura nylon' },
      { label: 'Strapping', value: 'Dual high-tension hook-and-loop wrap belt' }
    ],
    athlete_quote: 'Sits snug against the torso with zero bounce during explosive muscle-ups and handstand push-ups.'
  }
];

const TESTIMONIALS = [
  {
    name: 'Karan Sharma',
    role: 'National Calisthenics Athlete & Coach (Delhi)',
    comment: 'The 32mm Birch gymnastic rings and heavy dip belt have handled 300+ sessions without a single issue. The strap measurement marks make ring height alignment instant.',
    rating: 5,
    product: 'Olympic Birch Gymnastic Rings (32mm)'
  },
  {
    name: 'Aditi Deshmukh',
    role: 'CrossFit Athlete & Gymnastics Trainer (Mumbai)',
    comment: 'The 100% Whey Isolate is pure quality. It mixes cleanly without clumps, is easy on digestion, and the Belgian chocolate flavor is genuinely top tier.',
    rating: 5,
    product: '100% Whey Isolate (2kg)'
  },
  {
    name: 'Vikram Rajput',
    role: 'Street Workout Competitor (Bengaluru)',
    comment: 'Creapure grade creatine plus the liquid chalk have completely transformed my bar endurance. Delivery to Bengaluru took just 48 hours via express courier.',
    rating: 5,
    product: 'Creatine Monohydrate 250g'
  }
];

const FAQS = [
  {
    q: 'How fast is delivery and shipping handled across India?',
    a: 'All orders placed before 3:00 PM IST are dispatched within 24 hours from our regional logistics fulfillment centers. Delivery typically takes 2 to 4 business days to metro cities and 3 to 5 business days across all 26,000+ serviceable PIN codes in India. You will receive live tracking updates via SMS and WhatsApp.'
  },
  {
    q: 'Is Cash on Delivery (COD) supported?',
    a: 'Yes! We offer 100% verified Pan-India Cash on Delivery (COD) on all equipment and supplement orders. You can pay cash or scan the courier delivery agent’s UPI QR code upon arrival at your doorstep.'
  },
  {
    q: 'Can I track my order live on this storefront?',
    a: 'Absolutely. Every order generates an official order code (e.g. USA-RS-20261113-A1F). Simply click "Track Order" in the top navigation, enter your order code, and view real-time status progression from Order Placed to Dispatched and Delivered.'
  },
  {
    q: 'What is the warranty and return policy on Calisthenics equipment?',
    a: 'All USA–Raw Strength rings, parallettes, dip belts, and vests carry an unconditional 1-year replacement warranty against manufacturing defects, wood splintering, buckle slippage, or strap failure. We also provide a 7-day hassle-free replacement for any transit damage.'
  },
  {
    q: 'Are the sports nutrition supplements 100% authentic and lab-tested?',
    a: 'Yes. Every batch of USA–Raw Strength Whey Isolate and Micronized Creatine is third-party lab tested for purity, heavy metals, and banned substances with FSSAI & Informed-Choice compliance. Each tub features an authentic scratch-and-verify QR authenticity code.'
  }
];

export default function Storefront({ onBack }) {
  const [view, setView] = useState('catalog'); // 'catalog' | 'track'
  const [products, setProducts] = useState(FLAGSHIP_CATALOG);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Cart state persisted to localStorage
  const [cart, setCart] = useState(() => {
    try {
      const saved = localStorage.getItem('rsc_storefront_cart');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('rsc_storefront_cart', JSON.stringify(cart));
    } catch {}
  }, [cart]);

  // Drawer / Modal states
  const [cartOpen, setCartOpen] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [quickViewProduct, setQuickViewProduct] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [copiedCode, setCopiedCode] = useState(false);

  // Filters & Search
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [sortOption, setSortOption] = useState('featured');
  const [inStockOnly, setInStockOnly] = useState(false);

  // Coupon state
  const [couponInput, setCouponInput] = useState('');
  const [appliedCoupon, setAppliedCoupon] = useState(null); // { code, discount, type }
  const [couponError, setCouponError] = useState('');

  // Checkout form
  const [customer, setCustomer] = useState({
    customer_name: '',
    phone: '',
    email: '',
    shipping_address: '',
    pincode: '',
    customer_note: '',
    payment_method: 'Cash on Delivery',
    upi_ref: ''
  });
  const [submitting, setSubmitting] = useState(false);

  // Order Tracking state
  const [trackingCode, setTrackingCode] = useState('');
  const [trackingData, setTrackingData] = useState(null);
  const [trackingLoading, setTrackingLoading] = useState(false);
  const [trackingError, setTrackingError] = useState('');

  // FAQ accordion state
  const [openFaq, setOpenFaq] = useState(null);

  // Fetch catalog from D1 API and blend with flagship items
  useEffect(() => {
    api('/store/catalog')
      .then(rows => {
        if (Array.isArray(rows) && rows.length > 0) {
          // Merge D1 items with flagship catalog
          const d1Map = new Map();
          rows.forEach(r => {
            if (r.price > 0) d1Map.set(String(r.id), r);
          });
          const merged = FLAGSHIP_CATALOG.map(f => {
            const match = rows.find(r => r.sku && f.sku && r.sku.toLowerCase() === f.sku.toLowerCase());
            if (match) {
              return { ...f, id: match.id, price: Number(match.price) || f.price, available_stock: match.available_stock ?? f.available_stock };
            }
            return f;
          });
          // Add any other products from D1 not in flagship catalog
          rows.forEach(r => {
            const exists = merged.some(m => m.id === r.id || (m.sku && r.sku && m.sku.toLowerCase() === r.sku.toLowerCase()));
            if (!exists && r.price > 0) {
              merged.push({
                ...r,
                original_price: Math.round(r.price * 1.3),
                rating: 4.8,
                reviews_count: 25,
                badge: 'Official Gear',
                tagline: r.category || 'USA–Raw Strength Official Equipment',
                description: r.name + ' - Certified Calisthenics Equipment & Sports Nutrition by USA–Raw Strength.',
                specs: [{ label: 'Unit', value: r.unit || 'PCS' }]
              });
            }
          });
          setProducts(merged);
        }
      })
      .catch(() => {
        // Fallback to static flagship catalog smoothly
      })
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
    let result = products.filter(p => {
      if (categoryFilter !== 'All' && String(p.category || '').toLowerCase() !== categoryFilter.toLowerCase()) {
        return false;
      }
      if (inStockOnly && (p.available_stock || 0) < 1) {
        return false;
      }
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        const haystack = [p.name, p.category, p.brand, p.sku, p.package_type, p.tagline, p.description].filter(Boolean).join(' ').toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });

    if (sortOption === 'price_asc') {
      result.sort((a, b) => a.price - b.price);
    } else if (sortOption === 'price_desc') {
      result.sort((a, b) => b.price - a.price);
    } else if (sortOption === 'rating') {
      result.sort((a, b) => (b.rating || 0) - (a.rating || 0));
    }
    return result;
  }, [products, categoryFilter, inStockOnly, search, sortOption]);

  const cartItems = useMemo(
    () => products.filter(p => cart[p.id] > 0).map(p => ({ ...p, quantity: cart[p.id] })),
    [products, cart]
  );

  const subtotal = useMemo(() => cartItems.reduce((sum, p) => sum + p.price * p.quantity, 0), [cartItems]);
  const cartCount = useMemo(() => cartItems.reduce((sum, p) => sum + p.quantity, 0), [cartItems]);

  // Coupon calculations
  const discountAmount = useMemo(() => {
    if (!appliedCoupon) return 0;
    if (appliedCoupon.type === 'pct') {
      return Math.round((subtotal * appliedCoupon.value) / 100);
    }
    return 0;
  }, [appliedCoupon, subtotal]);

  const shippingFee = useMemo(() => {
    if (subtotal === 0) return 0;
    if (appliedCoupon?.type === 'freeship') return 0;
    if (subtotal >= 999) return 0;
    return 99; // Standard flat shipping under ₹999
  }, [subtotal, appliedCoupon]);

  const grandTotal = Math.max(0, subtotal - discountAmount + shippingFee);

  const setQty = (id, value) => {
    const product = products.find(p => String(p.id) === String(id));
    const limit = Math.min(100, Math.max(0, Math.floor(Number(product?.available_stock || 99))));
    const parsed = Math.max(0, Math.min(limit, Number(value) || 0));
    setCart(old => {
      const copy = { ...old };
      if (parsed === 0) {
        delete copy[id];
      } else {
        copy[id] = parsed;
      }
      return copy;
    });
  };

  const applyCoupon = e => {
    e?.preventDefault();
    setCouponError('');
    const code = couponInput.trim().toUpperCase();
    if (!code) return;
    if (code === 'RAW10') {
      setAppliedCoupon({ code: 'RAW10', type: 'pct', value: 10, label: '10% Instant Discount' });
      setCouponInput('');
    } else if (code === 'FREESHIP') {
      setAppliedCoupon({ code: 'FREESHIP', type: 'freeship', value: 0, label: 'Free Express Shipping' });
      setCouponInput('');
    } else {
      setCouponError('Invalid coupon code. Try RAW10 or FREESHIP');
    }
  };

  const removeCoupon = () => {
    setAppliedCoupon(null);
    setCouponError('');
  };

  const handleOrderSubmit = async e => {
    e.preventDefault();
    if (cartItems.length === 0) return;
    setSubmitting(true);
    setError('');

    const phoneClean = customer.phone.replace(/\D/g, '');
    if (phoneClean.length < 10) {
      setError('Please enter a valid 10-digit mobile phone number.');
      setSubmitting(false);
      return;
    }

    try {
      const payload = {
        customer_name: customer.customer_name,
        phone: customer.phone,
        email: customer.email,
        shipping_address: customer.shipping_address + (customer.pincode ? ` - PIN: ${customer.pincode}` : ''),
        customer_note: [customer.customer_note, customer.upi_ref ? `UPI Ref: ${customer.upi_ref}` : ''].filter(Boolean).join(' | '),
        payment_method: customer.payment_method,
        payment_status: customer.payment_method === 'Cash on Delivery' ? 'Unpaid' : 'Pending Verification',
        items: cartItems.map(p => ({
          product_id: p.id,
          product_name: p.name,
          sku: p.sku || '',
          quantity: p.quantity,
          unit: p.unit || 'PCS',
          unit_price: p.price
        }))
      };

      const result = await api('/store/orders', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      setReceipt({
        ...result,
        customer_name: customer.customer_name,
        phone: customer.phone,
        email: customer.email,
        shipping_address: payload.shipping_address,
        payment_method: customer.payment_method,
        items: cartItems,
        subtotal,
        discount: discountAmount,
        shipping: shippingFee,
        total_amount: grandTotal
      });

      setCart({});
      setCheckoutOpen(false);
      setCartOpen(false);
    } catch (err) {
      setError(err.message || 'Failed to submit order. Please check connection.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleTrackLookup = async codeToLook => {
    const code = (codeToLook || trackingCode).trim();
    if (!code) {
      setTrackingError('Please enter an order code (e.g. USA-RS-...)');
      return;
    }
    setTrackingLoading(true);
    setTrackingError('');
    setTrackingData(null);
    try {
      const data = await api(`/store/track?code=${encodeURIComponent(code)}`);
      setTrackingData(data);
    } catch (err) {
      setTrackingError(err.message || 'No order found with this code. Check your code and try again.');
    } finally {
      setTrackingLoading(false);
    }
  };

  const copyOrderCode = code => {
    if (!code) return;
    navigator.clipboard?.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
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
    <div className="min-h-screen bg-[#060a12] text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-950">
      {/* 1. TOP ANNOUNCEMENT TICKER */}
      <div className="border-b border-cyan-500/20 bg-gradient-to-r from-cyan-950 via-slate-950 to-indigo-950 px-4 py-2 text-center text-xs text-slate-300">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div className="flex items-center gap-2 overflow-hidden text-ellipsis whitespace-nowrap text-xs font-medium text-cyan-200">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-cyan-400/20 px-2.5 py-0.5 text-[11px] font-bold text-cyan-300">
              <Truck size={13} /> FREE SHIPPING
            </span>
            <span>Free Express Delivery across India on orders over ₹999</span>
            <span className="hidden md:inline text-white/30">•</span>
            <span className="hidden md:inline">Use Code <strong className="text-cyan-300 font-bold">RAW10</strong> for 10% Off</span>
          </div>
          <div className="hidden sm:flex items-center gap-4 text-[11px] text-slate-400 shrink-0">
            <span className="inline-flex items-center gap-1"><ShieldCheck size={13} className="text-emerald-400" /> 100% Genuine Gear</span>
            <span className="inline-flex items-center gap-1"><RotateCcw size={13} className="text-cyan-400" /> 7-Day Replacement</span>
            <span className="inline-flex items-center gap-1"><CreditCard size={13} className="text-amber-400" /> Pan-India COD</span>
          </div>
        </div>
      </div>

      {/* 2. MAIN HEADER & NAVBAR */}
      <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          {/* Logo & Brand Identity */}
          <div className="flex items-center gap-3">
            <div
              onClick={() => { setView('catalog'); setReceipt(null); }}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <div className="relative grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition">
                <Store size={22} className="text-slate-950" />
              </div>
              <div>
                <strong className="block text-base font-black tracking-wider text-white group-hover:text-cyan-300 transition">
                  USA–RAW STRENGTH
                </strong>
                <span className="text-[11px] text-slate-400 font-medium tracking-tight">
                  United Sciences Alliance · Official Store
                </span>
              </div>
            </div>
          </div>

          {/* Nav Links */}
          <nav className="hidden lg:flex items-center gap-1">
            <button
              onClick={() => { setView('catalog'); setReceipt(null); }}
              className={`rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                view === 'catalog' && !receipt ? 'bg-cyan-400/15 text-cyan-300 border border-cyan-400/30' : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              Shop Catalog
            </button>
            <button
              onClick={() => { setView('track'); setReceipt(null); }}
              className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                view === 'track' ? 'bg-cyan-400/15 text-cyan-300 border border-cyan-400/30' : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <Package size={14} /> Track Order
            </button>
            <a
              href="#reviews"
              onClick={() => setView('catalog')}
              className="rounded-xl px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-white/5 transition"
            >
              Athlete Reviews
            </a>
            <a
              href="#faq"
              onClick={() => setView('catalog')}
              className="rounded-xl px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-white/5 transition"
            >
              FAQ
            </a>
          </nav>

          {/* Right Action Buttons */}
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              onClick={() => { setView('track'); setReceipt(null); }}
              className="sm:hidden inline-flex items-center gap-1 rounded-xl border border-white/10 px-2.5 py-2 text-xs font-semibold text-slate-300 hover:bg-white/5"
              title="Track Order"
            >
              <Package size={15} />
            </button>

            <button
              onClick={() => setCartOpen(true)}
              className="relative inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-400 px-3.5 py-2 text-xs sm:text-sm font-bold text-slate-950 shadow-lg shadow-cyan-400/20 hover:from-cyan-400 hover:to-cyan-300 transition"
            >
              <ShoppingCart size={17} />
              <span className="hidden sm:inline">Cart</span>
              <span className="grid h-5 w-5 place-items-center rounded-full bg-slate-950 text-[11px] font-black text-cyan-300">
                {cartCount}
              </span>
              {subtotal > 0 && (
                <span className="hidden md:inline pl-1 border-l border-slate-950/20 font-black">
                  {money(grandTotal)}
                </span>
              )}
            </button>

            {/* Discreet Operations OS backlink */}
            <button
              type="button"
              onClick={handleReturn}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-2.5 py-2 text-xs font-semibold text-slate-300 hover:bg-white/10 hover:text-cyan-200 transition"
              title="Return to Employee Operations Portal"
            >
              <ArrowLeft size={14} />
              <span className="hidden sm:inline">Operations OS</span>
            </button>
          </div>
        </div>
      </header>

      {/* 3. ORDER RECEIPT MODAL (If just submitted) */}
      {receipt && (
        <section className="mx-auto max-w-4xl px-4 py-8">
          <div className="rounded-3xl border border-emerald-400/30 bg-slate-900/90 p-6 sm:p-10 shadow-2xl backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-6">
              <div className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-500/20 text-emerald-400">
                  <CheckCircle2 size={28} />
                </div>
                <div>
                  <h2 className="text-xl sm:text-2xl font-black text-white">Order Confirmed!</h2>
                  <p className="text-xs text-slate-400">Thank you for ordering with USA–Raw Strength Calisthenics.</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-white/10"
                >
                  <Printer size={14} /> Print Receipt
                </button>
                <button
                  onClick={() => {
                    setView('track');
                    setTrackingCode(receipt.order_code);
                    handleTrackLookup(receipt.order_code);
                    setReceipt(null);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-400 px-3.5 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300"
                >
                  <Package size={14} /> Track Order Live
                </button>
              </div>
            </div>

            {/* Order Code Callout */}
            <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-cyan-400/30 bg-cyan-950/30 p-4 sm:p-5">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">Your Tracking Code</span>
                <div className="text-xl sm:text-2xl font-black text-white font-mono">{receipt.order_code}</div>
                <p className="text-xs text-slate-400 mt-0.5">Save this code to track your package delivery status in real-time.</p>
              </div>
              <button
                onClick={() => copyOrderCode(receipt.order_code)}
                className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-3.5 py-2 text-xs font-bold text-cyan-200 hover:bg-cyan-400/20"
              >
                {copiedCode ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                {copiedCode ? 'Copied to Clipboard!' : 'Copy Code'}
              </button>
            </div>

            {/* Live Progression Stepper */}
            <div className="mt-8">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Fulfillment Progression</h3>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {[
                  { title: 'Ordered', desc: 'Order received', active: true, done: true },
                  { title: 'Confirmed', desc: 'Stock verified', active: true, done: true },
                  { title: 'Packed', desc: 'Quality checked', active: false, done: false },
                  { title: 'Dispatched', desc: 'In express transit', active: false, done: false },
                  { title: 'Delivered', desc: 'At your doorstep', active: false, done: false }
                ].map((step, idx) => (
                  <div key={idx} className={`rounded-xl border p-3 ${step.done ? 'border-emerald-400/40 bg-emerald-950/20' : 'border-white/5 bg-white/5'}`}>
                    <div className="flex items-center gap-2">
                      <span className={`grid h-5 w-5 place-items-center rounded-full text-[10px] font-bold ${step.done ? 'bg-emerald-400 text-slate-950' : 'bg-slate-800 text-slate-400'}`}>
                        {step.done ? '✓' : idx + 1}
                      </span>
                      <strong className={`text-xs ${step.done ? 'text-emerald-300' : 'text-slate-400'}`}>{step.title}</strong>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{step.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Order Summary & Customer Details */}
            <div className="mt-8 grid gap-6 md:grid-cols-2 border-t border-white/10 pt-6">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Delivery Details</h3>
                <p className="text-sm font-bold text-white">{receipt.customer_name}</p>
                <p className="text-xs text-slate-300 mt-1 flex items-center gap-1.5"><Phone size={13} className="text-cyan-400" /> {receipt.phone}</p>
                {receipt.email && <p className="text-xs text-slate-300 mt-1 flex items-center gap-1.5"><Mail size={13} className="text-cyan-400" /> {receipt.email}</p>}
                <p className="text-xs text-slate-300 mt-1 flex items-start gap-1.5"><MapPin size={13} className="text-cyan-400 shrink-0 mt-0.5" /> {receipt.shipping_address}</p>
                <div className="mt-4 rounded-xl border border-white/10 bg-slate-950 p-3 text-xs">
                  <span className="text-slate-400">Payment Method:</span>{' '}
                  <strong className="text-white">{receipt.payment_method}</strong>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Items Ordered</h3>
                <div className="space-y-2 rounded-2xl border border-white/10 bg-slate-950 p-4">
                  {receipt.items?.map((it, idx) => (
                    <div key={idx} className="flex items-center justify-between gap-2 text-xs py-1 border-b border-white/5 last:border-0">
                      <span className="text-slate-200">{it.name} <span className="text-slate-400">x {it.quantity}</span></span>
                      <span className="font-mono font-bold text-white">{money(it.price * it.quantity)}</span>
                    </div>
                  ))}
                  <div className="pt-2 border-t border-white/10 flex justify-between text-xs text-slate-400">
                    <span>Subtotal:</span> <span>{money(receipt.subtotal)}</span>
                  </div>
                  {receipt.discount > 0 && (
                    <div className="flex justify-between text-xs text-emerald-400">
                      <span>Discount:</span> <span>-{money(receipt.discount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-xs text-slate-400">
                    <span>Shipping:</span> <span>{receipt.shipping === 0 ? 'FREE' : money(receipt.shipping)}</span>
                  </div>
                  <div className="pt-2 border-t border-white/10 flex justify-between text-sm font-black text-white">
                    <span>Total Amount:</span> <span className="text-cyan-300">{money(receipt.total_amount)}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 flex justify-center">
              <button
                onClick={() => { setReceipt(null); setView('catalog'); }}
                className="rounded-xl border border-white/15 bg-white/5 px-6 py-2.5 text-xs font-bold text-slate-200 hover:bg-white/10 transition"
              >
                ← Return to Catalog
              </button>
            </div>
          </div>
        </section>
      )}

      {/* 4. TRACK ORDER VIEW */}
      {view === 'track' && !receipt && (
        <section className="mx-auto max-w-4xl px-4 py-8 sm:py-12">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-cyan-300">Live Logistics Gateway</span>
              <h1 className="text-2xl sm:text-4xl font-black text-white">Track Your Order</h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-1">
                Enter your USA-RS order code to inspect real-time courier and packaging telemetry.
              </p>
            </div>
            <button
              onClick={() => setView('catalog')}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-white/10"
            >
              <ArrowLeft size={14} /> Back to Catalog
            </button>
          </div>

          {/* Search Box */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4 sm:p-6 shadow-xl">
            <form
              onSubmit={e => { e.preventDefault(); handleTrackLookup(); }}
              className="flex flex-col sm:flex-row gap-3"
            >
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-3.5 text-slate-400" size={17} />
                <input
                  value={trackingCode}
                  onChange={e => setTrackingCode(e.target.value)}
                  placeholder="Enter order code (e.g. USA-RS-20261113-A1F)"
                  className="w-full rounded-xl border border-white/10 bg-slate-950 py-3 pl-10 pr-4 text-sm text-white font-mono outline-none focus:border-cyan-400"
                />
              </div>
              <button
                type="submit"
                disabled={trackingLoading}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 px-6 py-3 text-sm font-bold text-slate-950 hover:bg-cyan-300 transition disabled:opacity-50"
              >
                {trackingLoading ? 'Checking…' : 'Track Order'}
              </button>
            </form>

            {/* Demo / Sample Codes Pill */}
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
              <span>Quick sample search:</span>
              <button
                type="button"
                onClick={() => { setTrackingCode('USA-RS-20261113-XYZ'); handleTrackLookup('USA-RS-20261113-XYZ'); }}
                className="rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-1 text-[11px] font-mono text-cyan-300 hover:bg-cyan-400/20"
              >
                USA-RS-20261113-XYZ
              </button>
            </div>
          </div>

          {trackingError && (
            <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-950/40 p-4 text-xs sm:text-sm text-rose-200">
              {trackingError}
            </div>
          )}

          {/* Live Order Details Card */}
          {trackingData && (
            <div className="mt-6 rounded-3xl border border-white/10 bg-slate-900/90 p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Official Order Code</span>
                  <div className="text-xl font-black text-white font-mono">{trackingData.order_code}</div>
                  <div className="text-xs text-slate-400 mt-0.5">Placed on: {new Date(trackingData.created_at || Date.now()).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-bold text-cyan-300">
                    Status: {trackingData.order_status || 'Pending'}
                  </span>
                  <span className={`rounded-full border px-3 py-1 text-xs font-bold ${
                    trackingData.payment_status === 'Paid' ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300' : 'border-amber-400/30 bg-amber-400/10 text-amber-300'
                  }`}>
                    {trackingData.payment_status || 'Unpaid'}
                  </span>
                </div>
              </div>

              {/* Progress Stepper */}
              <div className="mt-6">
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {[
                    { title: 'Ordered', step: 1, req: 'Pending' },
                    { title: 'Confirmed', step: 2, req: 'Confirmed' },
                    { title: 'Packed', step: 3, req: 'Packed' },
                    { title: 'Dispatched', step: 4, req: 'Dispatched' },
                    { title: 'Delivered', step: 5, req: 'Delivered' }
                  ].map((s, idx) => {
                    const statusOrder = ['Pending', 'Confirmed', 'Packed', 'Dispatched', 'Delivered'];
                    const currentIdx = statusOrder.indexOf(trackingData.order_status || 'Pending');
                    const isDone = currentIdx >= idx;
                    const isCurrent = currentIdx === idx;
                    return (
                      <div key={idx} className={`rounded-xl border p-3 ${isCurrent ? 'border-cyan-400 bg-cyan-950/30' : isDone ? 'border-emerald-400/30 bg-emerald-950/20' : 'border-white/5 bg-white/5 opacity-60'}`}>
                        <div className="flex items-center gap-2">
                          <span className={`grid h-5 w-5 place-items-center rounded-full text-[10px] font-bold ${isDone ? 'bg-emerald-400 text-slate-950' : 'bg-slate-800 text-slate-400'}`}>
                            {isDone ? '✓' : idx + 1}
                          </span>
                          <strong className={`text-xs ${isCurrent ? 'text-cyan-300' : isDone ? 'text-emerald-300' : 'text-slate-400'}`}>
                            {s.title}
                          </strong>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-1">{isCurrent ? 'Current stage' : isDone ? 'Completed' : 'Upcoming'}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Items & Shipping Details */}
              <div className="mt-6 grid gap-6 md:grid-cols-2 border-t border-white/10 pt-5 text-xs">
                <div>
                  <h4 className="font-bold uppercase tracking-wider text-slate-400 mb-2">Recipient & Shipping</h4>
                  <p className="text-sm font-bold text-white">{trackingData.customer_name}</p>
                  <p className="text-slate-300 mt-1">Phone: {trackingData.phone}</p>
                  {trackingData.email && <p className="text-slate-300 mt-1">Email: {trackingData.email}</p>}
                  <p className="text-slate-300 mt-1 leading-relaxed">Delivery: {trackingData.shipping_address}</p>
                  <p className="text-slate-400 mt-2">Payment Method: <span className="text-white font-medium">{trackingData.payment_method || 'Cash on Delivery'}</span></p>
                </div>

                <div>
                  <h4 className="font-bold uppercase tracking-wider text-slate-400 mb-2">Package Contents</h4>
                  <div className="space-y-2 rounded-xl border border-white/10 bg-slate-950 p-3">
                    {trackingData.items?.length ? (
                      trackingData.items.map((it, idx) => (
                        <div key={idx} className="flex items-center justify-between gap-2 border-b border-white/5 pb-1.5 last:border-0 last:pb-0">
                          <div>
                            <span className="font-semibold text-white">{it.product_name}</span>
                            <span className="text-slate-400 ml-2">x {it.quantity} {it.unit || 'PCS'}</span>
                            {it.sku && <div className="text-[10px] text-cyan-400 font-mono">SKU: {it.sku}</div>}
                          </div>
                          <span className="font-mono text-white font-bold">{money(it.line_total || (it.unit_price * it.quantity))}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-slate-400">Order items recorded.</p>
                    )}
                    <div className="pt-2 border-t border-white/10 flex justify-between font-bold text-sm text-white">
                      <span>Total Amount:</span>
                      <span className="text-cyan-300">{money(trackingData.total_amount)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* 5. HERO SECTION (CATALOG VIEW) */}
      {view === 'catalog' && !receipt && (
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <section className="relative mb-10 overflow-hidden rounded-3xl border border-cyan-400/20 bg-gradient-to-br from-cyan-950 via-slate-950 to-indigo-950 p-6 sm:p-12 shadow-2xl">
            {/* Ambient background glows */}
            <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
            <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

            <div className="relative z-10 max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-bold text-cyan-300 mb-4">
                <Sparkles size={13} /> OFFICIAL CALISTHENICS &amp; PERFORMANCE STORE · INDIA
              </div>
              <h1 className="text-3xl font-black tracking-tight text-white sm:text-5xl lg:text-6xl leading-[1.1]">
                Forge Unstoppable <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-indigo-300">Raw Strength</span>
              </h1>
              <p className="mt-4 text-sm sm:text-base leading-relaxed text-slate-300 max-w-2xl">
                Competition-grade 32mm Baltic birch gymnastic rings, ergonomic beech parallettes, heavy-duty weighted dip belts, and ultra-filtered sports nutrition engineered for serious bodyweight athletes.
              </p>

              {/* Value Pillar Badges */}
              <div className="mt-6 flex flex-wrap gap-2.5 text-xs text-slate-300">
                <span className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-1.5 backdrop-blur-md flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-emerald-400" /> 100% Certified Lab-Tested
                </span>
                <span className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-1.5 backdrop-blur-md flex items-center gap-1.5">
                  <Truck size={14} className="text-cyan-400" /> 48-Hour Dispatch across India
                </span>
                <span className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-1.5 backdrop-blur-md flex items-center gap-1.5">
                  <CreditCard size={14} className="text-amber-400" /> Cash on Delivery Available
                </span>
              </div>

              {/* Quick Action CTAs */}
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <a
                  href="#catalog"
                  className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-5 py-3 text-sm font-bold text-slate-950 hover:bg-cyan-300 transition shadow-lg shadow-cyan-400/20"
                >
                  Explore Catalog <ArrowRight size={16} />
                </a>
                <button
                  onClick={() => setView('track')}
                  className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-5 py-3 text-sm font-bold text-white hover:bg-white/10 transition"
                >
                  <Package size={16} className="text-cyan-300" /> Track Existing Order
                </button>
              </div>
            </div>
          </section>

          {/* 6. SEARCH & FILTER CONTROLS */}
          <section id="catalog" className="mb-8 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Search input */}
              <div className="relative min-w-[280px] flex-1 max-w-md">
                <Search className="absolute left-3.5 top-3.5 text-slate-400" size={16} />
                <input
                  className="w-full rounded-xl border border-white/10 bg-slate-900/90 py-2.5 pl-10 pr-4 text-xs sm:text-sm text-white outline-none focus:border-cyan-400"
                  placeholder="Search gear, rings, whey isolate, creatine, chalk..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
                {search && (
                  <button
                    onClick={() => setSearch('')}
                    className="absolute right-3 top-3 text-slate-400 hover:text-white"
                  >
                    <X size={15} />
                  </button>
                )}
              </div>

              {/* Sort & In-Stock Toggles */}
              <div className="flex flex-wrap items-center gap-2.5">
                <select
                  value={sortOption}
                  onChange={e => setSortOption(e.target.value)}
                  className="rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-300 outline-none focus:border-cyan-400"
                >
                  <option value="featured">Featured / Bestsellers</option>
                  <option value="price_asc">Price: Low to High</option>
                  <option value="price_desc">Price: High to Low</option>
                  <option value="rating">Highest Customer Rating</option>
                </select>

                <button
                  type="button"
                  onClick={() => setInStockOnly(!inStockOnly)}
                  className={`rounded-xl border px-3 py-2 text-xs font-semibold transition ${
                    inStockOnly
                      ? 'border-emerald-400/40 bg-emerald-950/40 text-emerald-300'
                      : 'border-white/10 bg-slate-900 text-slate-400 hover:text-white'
                  }`}
                >
                  {inStockOnly ? '✓ In Stock Only' : 'Show All Stock'}
                </button>

                <span className="text-xs text-slate-400 font-medium ml-1">
                  {filteredProducts.length} items
                </span>
              </div>
            </div>

            {/* Category Filter Pills */}
            <div className="flex flex-wrap gap-2 pt-1">
              {categories.map(cat => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategoryFilter(cat)}
                  className={`rounded-xl border px-3.5 py-1.5 text-xs font-bold transition ${
                    categoryFilter === cat
                      ? 'border-cyan-400 bg-cyan-400 text-slate-950 shadow-md shadow-cyan-400/20'
                      : 'border-white/10 bg-slate-900/80 text-slate-300 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </section>

          {/* 7. PRODUCT CATALOG GRID */}
          <section className="mb-16">
            {filteredProducts.length > 0 ? (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {filteredProducts.map(p => {
                  const qtyInCart = cart[p.id] || 0;
                  const savings = p.original_price ? p.original_price - p.price : 0;
                  return (
                    <article
                      key={p.id}
                      className="group flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-900/80 p-4 shadow-xl transition-all duration-200 hover:-translate-y-1 hover:border-cyan-400/50 hover:shadow-cyan-500/10"
                    >
                      <div>
                        {/* Visual Image / Placeholder */}
                        <div className="relative aspect-[4/3] w-full overflow-hidden rounded-xl bg-gradient-to-br from-slate-800 to-slate-950 flex flex-col items-center justify-center p-4">
                          <ShoppingBag size={48} className="text-cyan-400/70 group-hover:scale-110 transition duration-300" />
                          <span className="mt-2 text-[11px] font-mono font-medium text-slate-400">{p.sku}</span>

                          {/* Badges */}
                          <div className="absolute left-2.5 top-2.5 flex flex-col gap-1">
                            {p.badge && (
                              <span className="rounded-lg bg-cyan-400 px-2 py-0.5 text-[10px] font-extrabold text-slate-950 shadow">
                                {p.badge}
                              </span>
                            )}
                            {savings > 0 && (
                              <span className="rounded-lg bg-emerald-500/90 px-2 py-0.5 text-[10px] font-bold text-white shadow">
                                Save {money(savings)}
                              </span>
                            )}
                          </div>

                          <button
                            type="button"
                            onClick={() => setQuickViewProduct(p)}
                            className="absolute right-2.5 bottom-2.5 rounded-lg border border-white/20 bg-slate-950/80 px-2 py-1 text-[11px] font-semibold text-slate-300 opacity-0 group-hover:opacity-100 transition backdrop-blur-sm hover:text-white"
                          >
                            Quick View
                          </button>
                        </div>

                        {/* Product Info */}
                        <div className="mt-4">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold uppercase tracking-wider text-cyan-300">{p.category}</span>
                            <span className="flex items-center gap-1 text-amber-400 font-bold">
                              <Star size={12} fill="currentColor" /> {p.rating || 4.9}
                              <span className="text-slate-500 font-normal">({p.reviews_count || 50})</span>
                            </span>
                          </div>

                          <h3
                            onClick={() => setQuickViewProduct(p)}
                            className="mt-1 font-bold text-white text-base leading-snug line-clamp-2 cursor-pointer hover:text-cyan-300 transition"
                          >
                            {p.name}
                          </h3>

                          <p className="mt-1 text-xs text-slate-400 line-clamp-2">
                            {p.tagline || p.description}
                          </p>

                          {/* Pricing & Stock */}
                          <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-xl font-black text-white">{money(p.price)}</span>
                            {p.original_price && p.original_price > p.price && (
                              <span className="text-xs text-slate-500 line-through">{money(p.original_price)}</span>
                            )}
                            <span className="text-[11px] text-slate-400 font-normal">/ {p.unit || 'PCS'}</span>
                          </div>

                          <div className="mt-1 text-xs">
                            {p.available_stock > 0 ? (
                              <span className="text-emerald-400 font-medium flex items-center gap-1">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> In Stock ({p.available_stock} {p.unit || 'units'})
                              </span>
                            ) : (
                              <span className="text-rose-400 font-medium">Out of stock</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Action Button */}
                      <div className="mt-4 pt-3 border-t border-white/5 flex items-center gap-2">
                        {qtyInCart > 0 ? (
                          <div className="flex w-full items-center justify-between rounded-xl border border-cyan-400/40 bg-cyan-950/30 p-1">
                            <button
                              onClick={() => setQty(p.id, qtyInCart - 1)}
                              className="rounded-lg p-1.5 text-cyan-300 hover:bg-cyan-400/20"
                            >
                              <Minus size={15} />
                            </button>
                            <span className="font-bold text-sm text-cyan-200">{qtyInCart} in Cart</span>
                            <button
                              onClick={() => setQty(p.id, qtyInCart + 1)}
                              disabled={qtyInCart >= p.available_stock}
                              className="rounded-lg p-1.5 text-cyan-300 hover:bg-cyan-400/20 disabled:opacity-40"
                            >
                              <Plus size={15} />
                            </button>
                          </div>
                        ) : (
                          <button
                            disabled={p.available_stock < 1}
                            onClick={() => { setQty(p.id, 1); setCartOpen(true); }}
                            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <ShoppingCart size={15} /> Add to Cart
                          </button>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-12 text-center max-w-xl mx-auto">
                <ShoppingBag className="mx-auto text-slate-600 mb-3" size={40} />
                <h3 className="text-base font-bold text-white">No products found</h3>
                <p className="text-xs text-slate-400 mt-1">Try resetting search filters or selecting 'All' categories.</p>
                <button
                  onClick={() => { setSearch(''); setCategoryFilter('All'); setInStockOnly(false); }}
                  className="mt-4 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-xs font-bold text-cyan-300 hover:bg-cyan-400/20"
                >
                  Reset All Filters
                </button>
              </div>
            )}
          </section>

          {/* 8. ATHLETE TESTIMONIALS SECTION */}
          <section id="reviews" className="mb-16 border-t border-white/10 pt-12">
            <div className="text-center max-w-2xl mx-auto mb-8">
              <span className="text-xs font-bold uppercase tracking-widest text-cyan-300">Verified Proof</span>
              <h2 className="text-2xl sm:text-3xl font-black text-white mt-1">Trusted by Elite Calisthenics Athletes</h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-2">
                Real feedback from competitive gymnasts, street workout athletes, and national strength coaches across India.
              </p>
            </div>

            <div className="grid gap-5 md:grid-cols-3">
              {TESTIMONIALS.map((t, idx) => (
                <div key={idx} className="flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-900/70 p-5 shadow-xl">
                  <div>
                    <div className="flex items-center gap-1 text-amber-400 mb-3">
                      {[...Array(t.rating)].map((_, i) => (
                        <Star key={i} size={14} fill="currentColor" />
                      ))}
                    </div>
                    <p className="text-xs sm:text-sm text-slate-300 italic leading-relaxed">
                      "{t.comment}"
                    </p>
                  </div>
                  <div className="mt-5 border-t border-white/5 pt-3">
                    <p className="font-bold text-white text-xs sm:text-sm">{t.name}</p>
                    <p className="text-[11px] text-cyan-400">{t.role}</p>
                    <span className="mt-1 inline-block text-[10px] text-slate-500">Verified purchase: {t.product}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 9. FAQ ACCORDION */}
          <section id="faq" className="mb-16 border-t border-white/10 pt-12 max-w-3xl mx-auto">
            <div className="text-center mb-8">
              <span className="text-xs font-bold uppercase tracking-widest text-cyan-300">Got Questions?</span>
              <h2 className="text-2xl sm:text-3xl font-black text-white mt-1">Frequently Asked Questions</h2>
            </div>

            <div className="space-y-3">
              {FAQS.map((faq, idx) => {
                const isOpen = openFaq === idx;
                return (
                  <div key={idx} className="rounded-2xl border border-white/10 bg-slate-900/60 overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setOpenFaq(isOpen ? null : idx)}
                      className="w-full flex items-center justify-between p-4 sm:p-5 text-left text-xs sm:text-sm font-bold text-white hover:text-cyan-300 transition"
                    >
                      <span>{faq.q}</span>
                      {isOpen ? <ChevronUp size={16} className="text-cyan-400 shrink-0" /> : <ChevronDown size={16} className="text-slate-400 shrink-0" />}
                    </button>
                    {isOpen && (
                      <div className="px-4 pb-4 sm:px-5 sm:pb-5 text-xs sm:text-sm leading-relaxed text-slate-300 border-t border-white/5 pt-3">
                        {faq.a}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </main>
      )}

      {/* 10. PRODUCT QUICK VIEW MODAL */}
      {quickViewProduct && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md"
          role="presentation"
          onClick={e => { if (e.target === e.currentTarget) setQuickViewProduct(null); }}
        >
          <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-white/15 bg-slate-950 p-6 sm:p-8 shadow-2xl">
            <button
              onClick={() => setQuickViewProduct(null)}
              className="absolute right-4 top-4 rounded-xl p-2 text-slate-400 hover:bg-white/10 hover:text-white"
            >
              <X size={18} />
            </button>

            <div className="flex flex-col sm:flex-row gap-6">
              <div className="grid aspect-square sm:w-1/2 place-items-center rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-white/10 p-6 text-cyan-400">
                <ShoppingBag size={80} />
                <span className="mt-3 text-xs font-mono text-slate-400">{quickViewProduct.sku}</span>
              </div>

              <div className="sm:w-1/2 flex flex-col justify-between">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">{quickViewProduct.category}</span>
                  <h2 className="text-xl font-black text-white mt-1 leading-snug">{quickViewProduct.name}</h2>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-2xl font-black text-white">{money(quickViewProduct.price)}</span>
                    {quickViewProduct.original_price && (
                      <span className="text-sm text-slate-500 line-through">{money(quickViewProduct.original_price)}</span>
                    )}
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-slate-300">{quickViewProduct.description}</p>
                </div>

                <div className="mt-6 pt-4 border-t border-white/10">
                  <div className="mb-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Technical Specifications</h4>
                    <div className="space-y-1 text-xs">
                      {quickViewProduct.specs?.map((s, idx) => (
                        <div key={idx} className="flex justify-between py-0.5 border-b border-white/5">
                          <span className="text-slate-400">{s.label}:</span>
                          <span className="text-white font-medium text-right">{s.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    disabled={quickViewProduct.available_stock < 1}
                    onClick={() => {
                      setQty(quickViewProduct.id, (cart[quickViewProduct.id] || 0) + 1);
                      setQuickViewProduct(null);
                      setCartOpen(true);
                    }}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 py-3 text-xs sm:text-sm font-bold text-slate-950 hover:bg-cyan-300 transition"
                  >
                    <ShoppingCart size={16} /> Add to Cart ({money(quickViewProduct.price)})
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 11. SLIDE-OVER CART DRAWER */}
      {cartOpen && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm"
          role="presentation"
          onClick={e => { if (e.target === e.currentTarget) setCartOpen(false); }}
        >
          <aside className="h-full w-full max-w-md overflow-y-auto border-l border-white/10 bg-slate-950 p-5 sm:p-6 shadow-2xl flex flex-col justify-between">
            <div>
              {/* Drawer Header */}
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-2">
                  <ShoppingCart size={20} className="text-cyan-400" />
                  <h2 className="text-lg font-black text-white">Your Shopping Cart</h2>
                  <span className="rounded-full bg-cyan-400/20 px-2 py-0.5 text-xs font-bold text-cyan-300">
                    {cartCount}
                  </span>
                </div>
                <button
                  onClick={() => setCartOpen(false)}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Free Shipping Progress Bar */}
              <div className="my-4 rounded-xl border border-cyan-400/20 bg-cyan-950/30 p-3">
                <div className="flex items-center justify-between text-xs mb-1.5 font-medium">
                  {subtotal >= 999 || appliedCoupon?.type === 'freeship' ? (
                    <span className="text-emerald-400 font-bold flex items-center gap-1">
                      <CheckCircle2 size={13} /> Free Express Shipping Unlocked!
                    </span>
                  ) : (
                    <span className="text-slate-300">
                      Add <strong className="text-cyan-300">{money(999 - subtotal)}</strong> more for FREE Shipping!
                    </span>
                  )}
                  <span className="text-slate-400">{Math.min(100, Math.round((subtotal / 999) * 100))}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all duration-300"
                    style={{ width: `${Math.min(100, (subtotal / 999) * 100)}%` }}
                  />
                </div>
              </div>

              {/* Cart Items List */}
              {cartItems.length > 0 ? (
                <div className="space-y-3">
                  {cartItems.map(p => (
                    <div key={p.id} className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-900/80 p-3">
                      <div className="min-w-0 flex-1">
                        <h4 className="font-bold text-xs sm:text-sm text-white truncate">{p.name}</h4>
                        <span className="text-xs text-slate-400">{money(p.price)} each</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex items-center rounded-lg border border-white/10 bg-slate-950">
                          <button
                            onClick={() => setQty(p.id, p.quantity - 1)}
                            className="p-1.5 text-slate-400 hover:text-white"
                          >
                            <Minus size={13} />
                          </button>
                          <span className="w-6 text-center text-xs font-bold text-white">{p.quantity}</span>
                          <button
                            onClick={() => setQty(p.id, p.quantity + 1)}
                            disabled={p.quantity >= p.available_stock}
                            className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30"
                          >
                            <Plus size={13} />
                          </button>
                        </div>
                        <span className="w-16 text-right font-mono text-xs font-bold text-white">
                          {money(p.price * p.quantity)}
                        </span>
                        <button
                          onClick={() => setQty(p.id, 0)}
                          className="text-slate-500 hover:text-rose-400 p-1"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}

                  {/* Coupon Code Section */}
                  <div className="pt-3 border-t border-white/10">
                    {appliedCoupon ? (
                      <div className="flex items-center justify-between rounded-xl border border-emerald-400/40 bg-emerald-950/20 px-3 py-2 text-xs">
                        <div className="flex items-center gap-1.5 text-emerald-300 font-bold">
                          <Tag size={13} /> {appliedCoupon.code} applied ({appliedCoupon.label})
                        </div>
                        <button
                          onClick={removeCoupon}
                          className="text-slate-400 hover:text-rose-400 font-semibold"
                        >
                          Remove
                        </button>
                      </div>
                    ) : (
                      <form onSubmit={applyCoupon} className="flex gap-2">
                        <input
                          value={couponInput}
                          onChange={e => setCouponInput(e.target.value)}
                          placeholder="Coupon code (e.g. RAW10)"
                          className="flex-1 rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white uppercase outline-none focus:border-cyan-400"
                        />
                        <button
                          type="submit"
                          className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3.5 py-2 text-xs font-bold text-cyan-300 hover:bg-cyan-400/20"
                        >
                          Apply
                        </button>
                      </form>
                    )}
                    {couponError && <p className="text-[11px] text-rose-400 mt-1">{couponError}</p>}
                  </div>
                </div>
              ) : (
                <div className="py-16 text-center text-slate-400 text-xs">
                  <ShoppingCart className="mx-auto mb-2 text-slate-600" size={32} />
                  Your cart is currently empty.
                </div>
              )}
            </div>

            {/* Cart Footer & Checkout Action */}
            {cartItems.length > 0 && (
              <div className="pt-4 border-t border-white/10 space-y-3">
                <div className="space-y-1.5 text-xs text-slate-300">
                  <div className="flex justify-between">
                    <span>Subtotal</span>
                    <span className="font-mono text-white">{money(subtotal)}</span>
                  </div>
                  {discountAmount > 0 && (
                    <div className="flex justify-between text-emerald-400">
                      <span>Coupon Discount</span>
                      <span className="font-mono">-{money(discountAmount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Estimated Shipping</span>
                    <span className="font-mono text-white">
                      {shippingFee === 0 ? <strong className="text-emerald-400">FREE</strong> : money(shippingFee)}
                    </span>
                  </div>
                  <div className="pt-2 border-t border-white/10 flex justify-between text-sm font-black text-white">
                    <span>Grand Total</span>
                    <span className="text-cyan-300 font-mono text-base">{money(grandTotal)}</span>
                  </div>
                </div>

                <button
                  onClick={() => { setCartOpen(false); setCheckoutOpen(true); }}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 py-3 text-sm font-bold text-slate-950 hover:bg-cyan-300 transition shadow-lg shadow-cyan-400/20"
                >
                  Proceed to Checkout · {money(grandTotal)} <ArrowRight size={16} />
                </button>
              </div>
            )}
          </aside>
        </div>
      )}

      {/* 12. CHECKOUT MODAL & PAYMENT SELECTION */}
      {checkoutOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md overflow-y-auto"
          role="presentation"
          onClick={e => { if (e.target === e.currentTarget) setCheckoutOpen(false); }}
        >
          <div className="relative my-8 max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-3xl border border-white/15 bg-slate-950 p-6 sm:p-8 shadow-2xl">
            <button
              onClick={() => setCheckoutOpen(false)}
              className="absolute right-4 top-4 rounded-xl p-2 text-slate-400 hover:bg-white/10 hover:text-white"
            >
              <X size={18} />
            </button>

            <div className="border-b border-white/10 pb-4 mb-6">
              <span className="text-xs font-bold uppercase tracking-widest text-cyan-300">USA–Raw Strength Store</span>
              <h2 className="text-xl font-black text-white mt-1">Delivery &amp; Checkout</h2>
              <p className="text-xs text-slate-400 mt-0.5">Please provide your delivery address and preferred payment method.</p>
            </div>

            {error && (
              <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-200">
                {error}
              </div>
            )}

            <form onSubmit={handleOrderSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">Full Name *</label>
                <input
                  required
                  maxLength={120}
                  value={customer.customer_name}
                  onChange={e => setCustomer({ ...customer, customer_name: e.target.value })}
                  placeholder="e.g. Rahul Sharma"
                  className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1">Mobile Phone Number *</label>
                  <input
                    required
                    maxLength={30}
                    value={customer.phone}
                    onChange={e => setCustomer({ ...customer, phone: e.target.value })}
                    placeholder="10-digit mobile number"
                    className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1">Email Address (Optional)</label>
                  <input
                    type="email"
                    value={customer.email}
                    onChange={e => setCustomer({ ...customer, email: e.target.value })}
                    placeholder="order updates via email"
                    className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">Complete Delivery Address *</label>
                <textarea
                  required
                  rows={2}
                  maxLength={1000}
                  value={customer.shipping_address}
                  onChange={e => setCustomer({ ...customer, shipping_address: e.target.value })}
                  placeholder="Flat/House No., Building, Street, Area, City, State"
                  className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1">PIN Code *</label>
                  <input
                    required
                    maxLength={10}
                    value={customer.pincode}
                    onChange={e => setCustomer({ ...customer, pincode: e.target.value })}
                    placeholder="6-digit Indian PIN code"
                    className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1">Delivery Notes (Optional)</label>
                  <input
                    value={customer.customer_note}
                    onChange={e => setCustomer({ ...customer, customer_note: e.target.value })}
                    placeholder="Gate code or instructions"
                    className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              {/* Payment Method Selection */}
              <div className="pt-2">
                <label className="block text-xs font-bold text-slate-300 mb-2">Select Payment Method</label>
                <div className="space-y-2">
                  {[
                    { id: 'Cash on Delivery', title: 'Cash on Delivery (COD)', desc: 'Pay cash or UPI to the courier agent upon doorstep delivery.', badge: 'Pan-India Available' },
                    { id: 'Instant UPI / QR', title: 'Instant UPI / QR Code', desc: 'Scan and pay instantly using Google Pay, PhonePe, Paytm, or BHIM.', badge: 'Fast Dispatch' },
                    { id: 'Credit / Debit Card', title: 'Credit / Debit Card / Net Banking', desc: 'Secure 128-bit encrypted card or online banking payment.', badge: 'Encrypted' }
                  ].map(m => (
                    <label
                      key={m.id}
                      className={`flex items-start gap-3 rounded-2xl border p-3.5 cursor-pointer transition ${
                        customer.payment_method === m.id ? 'border-cyan-400 bg-cyan-950/20' : 'border-white/10 bg-slate-900 hover:bg-white/5'
                      }`}
                    >
                      <input
                        type="radio"
                        name="payment_method"
                        checked={customer.payment_method === m.id}
                        onChange={() => setCustomer({ ...customer, payment_method: m.id })}
                        className="mt-0.5 text-cyan-400"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <strong className="text-xs font-bold text-white">{m.title}</strong>
                          <span className="rounded-md border border-cyan-400/30 bg-cyan-400/10 px-2 py-0.5 text-[10px] font-bold text-cyan-300">
                            {m.badge}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">{m.desc}</p>
                      </div>
                    </label>
                  ))}
                </div>

                {/* Instant UPI Simulator Details */}
                {customer.payment_method === 'Instant UPI / QR' && (
                  <div className="mt-3 rounded-2xl border border-cyan-400/30 bg-slate-900 p-4">
                    <div className="flex items-center gap-3">
                      <div className="grid h-16 w-16 place-items-center rounded-xl bg-white text-slate-950 p-1">
                        <QrCode size={48} />
                      </div>
                      <div className="text-xs">
                        <strong className="text-white block font-mono">rawstrength@upi</strong>
                        <p className="text-slate-400 text-[11px] mt-0.5">Scan with GPay, PhonePe, or Paytm.</p>
                        <p className="text-cyan-300 font-bold mt-1">Amount: {money(grandTotal)}</p>
                      </div>
                    </div>
                    <div className="mt-3">
                      <label className="block text-[11px] text-slate-400 mb-1">Enter UPI Reference / UTR Number (Optional)</label>
                      <input
                        value={customer.upi_ref}
                        onChange={e => setCustomer({ ...customer, upi_ref: e.target.value })}
                        placeholder="e.g. 412389123456"
                        className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white font-mono outline-none focus:border-cyan-400"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Order Final Total */}
              <div className="pt-3 border-t border-white/10 flex items-center justify-between">
                <div>
                  <span className="text-xs text-slate-400">Total Payable</span>
                  <div className="text-lg font-black text-cyan-300">{money(grandTotal)}</div>
                </div>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-6 py-3 text-sm font-bold text-slate-950 hover:bg-cyan-300 transition disabled:opacity-50"
                >
                  {submitting ? 'Placing Order…' : 'Place Order Now'} <Check size={16} />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 13. COMPREHENSIVE E-COMMERCE FOOTER */}
      <footer className="border-t border-white/10 bg-slate-950/90 pt-12 pb-8 text-xs text-slate-400">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4 pb-8 border-b border-white/10">
            <div>
              <div className="flex items-center gap-2 text-white font-black text-base">
                <Store size={18} className="text-cyan-400" /> USA–RAW STRENGTH
              </div>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                United Sciences Alliance · Professional Calisthenics &amp; Sports Nutrition Store. Engineered for competitive bodyweight athletes and strength enthusiasts across India.
              </p>
              <div className="mt-4 flex items-center gap-3 text-slate-400">
                <span className="text-[11px]">ISO 9001:2015 · FSSAI Certified</span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-white mb-3">Quick Navigation</h4>
              <ul className="space-y-2 text-xs">
                <li><button onClick={() => { setView('catalog'); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="hover:text-cyan-300 transition">Gymnastic Rings &amp; Straps</button></li>
                <li><button onClick={() => { setView('catalog'); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="hover:text-cyan-300 transition">Weighted Dip Belts</button></li>
                <li><button onClick={() => { setView('catalog'); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="hover:text-cyan-300 transition">Beech Parallettes</button></li>
                <li><button onClick={() => { setView('catalog'); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="hover:text-cyan-300 transition">100% Whey Isolate &amp; Creatine</button></li>
                <li><button onClick={() => setView('track')} className="text-cyan-300 font-bold hover:underline">Track Your Order Live</button></li>
              </ul>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-white mb-3">Customer Support</h4>
              <ul className="space-y-2 text-xs text-slate-300">
                <li className="flex items-center gap-2"><Phone size={13} className="text-cyan-400" /> +91 98765 43210</li>
                <li className="flex items-center gap-2"><Mail size={13} className="text-cyan-400" /> support@rawstrength.in</li>
                <li className="flex items-center gap-2"><Clock size={13} className="text-cyan-400" /> Mon–Sat: 9:00 AM – 7:00 PM IST</li>
                <li className="flex items-center gap-2"><MapPin size={13} className="text-cyan-400" /> Regional Hub, Bengaluru, India</li>
              </ul>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-white mb-3">Athlete Newsletter</h4>
              <p className="text-xs text-slate-400 mb-3">
                Subscribe for exclusive drop alerts, training blueprints, and 10% off your next purchase.
              </p>
              <form onSubmit={e => { e.preventDefault(); alert('Subscribed to Athlete Club!'); }} className="flex gap-2">
                <input
                  type="email"
                  required
                  placeholder="Your email address"
                  className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white outline-none focus:border-cyan-400"
                />
                <button
                  type="submit"
                  className="rounded-xl bg-cyan-400 px-3 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition"
                >
                  Join
                </button>
              </form>
            </div>
          </div>

          <div className="pt-6 flex flex-wrap items-center justify-between gap-4 text-[11px] text-slate-500">
            <div>
              © {new Date().getFullYear()} United Sciences Alliance · USA–Raw Strength Calisthenics. All rights reserved.
            </div>
            <div className="flex items-center gap-3">
              <span>Pan-India COD</span>
              <span>•</span>
              <span>UPI &amp; NetBanking</span>
              <span>•</span>
              <button onClick={handleReturn} className="text-cyan-400 font-bold hover:underline">
                Operations OS ↗
              </button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}