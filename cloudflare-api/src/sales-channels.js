const PLATFORMS = {
  amazon_india: { label: "Amazon India", auth: "lwa_sigv4", mode: "api", capabilities: ["orders","products","inventory_read","notifications"], docs: "https://developer-docs.amazon.com/sp-api/docs/onboarding-overview" },
  flipkart: { label: "Flipkart", auth: "seller_api_token", mode: "api", capabilities: ["orders","products","returns","notifications"], docs: "https://seller.flipkart.com/api-docs/index.html" },
  meesho: { label: "Meesho", auth: "partner_approved", mode: "partner_or_import", capabilities: ["orders_import"], docs: "https://supplier.meesho.com/" },
  shopify: { label: "Shopify", auth: "oauth_or_admin_token", mode: "api", capabilities: ["orders","products","inventory_read","webhooks"], docs: "https://shopify.dev/docs/api/admin-graphql" },
  woocommerce: { label: "WooCommerce", auth: "consumer_key_secret", mode: "api", capabilities: ["orders","products","inventory_read","webhooks"], docs: "https://developer.woocommerce.com/docs/apis/" },
  etsy: { label: "Etsy", auth: "oauth2", mode: "api", capabilities: ["orders","listings","inventory_read","webhooks"], docs: "https://developers.etsy.com/documentation/essentials/webhooks/" },
  ebay: { label: "eBay", auth: "oauth2", mode: "api", capabilities: ["orders","products","fulfillment"], docs: "https://developer.ebay.com/develop/api/sell/fulfillment_api" },
  other: { label: "Other", auth: "custom_adapter", mode: "custom_or_import", capabilities: ["orders_import","products_import","webhooks"], docs: "" }
};

const enc = new TextEncoder();
const dec = new TextDecoder();
const now = () => new Date().toISOString();
const safeJson = value => { try { return JSON.stringify(value ?? {}); } catch { return "{}"; } };
const hash = async value => hex(await crypto.subtle.digest("SHA-256", enc.encode(value)));
const hex = bytes => [...new Uint8Array(bytes)].map(v => v.toString(16).padStart(2,"0")).join("");
const randomToken = (n=32) => hex(crypto.getRandomValues(new Uint8Array(n)));
const all = async (db, sql, args=[]) => (await db.prepare(sql).bind(...args).all()).results || [];
const first = async (db, sql, args=[]) => db.prepare(sql).bind(...args).first();
const insert = async (db, table, fields) => {
  const keys = Object.keys(fields);
  const r = await db.prepare(`INSERT INTO ${table} (${keys.join(",")}) VALUES (${keys.map(()=>"?").join(",")})`).bind(...keys.map(k=>fields[k])).run();
  return Number(r.meta?.last_row_id || 0);
};
const publicChannel = row => ({
  id: row.id, platform: row.platform, label: PLATFORMS[row.platform]?.label || row.platform,
  account_label: row.account_label, status: row.status, auth_type: row.auth_type,
  created_at: row.created_at, updated_at: row.updated_at, last_sync_at: row.last_sync_at,
  last_error: row.last_error, webhook_url_path: `/api/sales-channels/${row.id}/webhook`,
  capabilities: PLATFORMS[row.platform]?.capabilities || []
});

async function encryptCredentials(env, value) {
  if (!env.CONNECTOR_ENCRYPTION_KEY) throw new Error("CONNECTOR_ENCRYPTION_KEY is not configured");
  const raw = Uint8Array.from(String(env.CONNECTOR_ENCRYPTION_KEY).match(/.{1,2}/g) || [], x => parseInt(x,16));
  if (raw.length !== 32) throw new Error("CONNECTOR_ENCRYPTION_KEY must be 64 hexadecimal characters");
  const key = await crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt"]);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const cipher = await crypto.subtle.encrypt({name:"AES-GCM",iv}, key, enc.encode(safeJson(value)));
  return hex(iv) + "." + hex(cipher);
}
async function decryptCredentials(env, value) {
  if (!env.CONNECTOR_ENCRYPTION_KEY) throw new Error("CONNECTOR_ENCRYPTION_KEY is not configured");
  const raw = Uint8Array.from(String(env.CONNECTOR_ENCRYPTION_KEY).match(/.{1,2}/g) || [], x => parseInt(x,16));
  if (raw.length !== 32) throw new Error("CONNECTOR_ENCRYPTION_KEY must be 64 hexadecimal characters");
  const [ivHex, cipherHex] = String(value||"").split(".");
  const bytes = s => Uint8Array.from((s.match(/.{1,2}/g)||[]),x=>parseInt(x,16));
  const key = await crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["decrypt"]);
  const plain = await crypto.subtle.decrypt({name:"AES-GCM",iv:bytes(ivHex)},key,bytes(cipherHex));
  return JSON.parse(dec.decode(plain));
}
function normalizeOrder(platform, raw) {
  const order = raw.order || raw.data?.order || raw;
  const id = String(order.id ?? order.order_id ?? order.orderId ?? order.receipt_id ?? order.name ?? "").trim();
  if (!id) throw new Error("Marketplace order is missing its external order ID");
  const itemsRaw = order.line_items || order.items || order.order_items || order.orderItems || order.products || [];
  const items = (Array.isArray(itemsRaw) ? itemsRaw : []).slice(0,100).map(item => ({
    external_item_id: String(item.id ?? item.order_item_id ?? item.line_item_id ?? ""),
    sku: String(item.sku ?? item.seller_sku ?? item.product_sku ?? ""),
    title: String(item.title ?? item.name ?? item.product_name ?? "Marketplace item").slice(0,300),
    quantity: Math.max(1, Math.min(100000, Number(item.quantity ?? item.qty ?? 1) || 1)),
    unit_price: Number(item.price ?? item.unit_price ?? item.item_price ?? 0) || 0,
    currency: String(item.currency ?? order.currency ?? "INR").slice(0,8)
  }));
  const customer = order.customer || order.billing || order.billing_address || order.billingAddress ||
    order.shipping_address || order.shippingAddress || {};
  const created = order.created_at || order.createdAt || order.date_created || order.date_created_gmt ||
    order.order_date || order.purchase_date || now();
  return {
    external_order_id: id, external_status: String(order.status ?? order.order_status ?? order.fulfillment_status ?? "new").slice(0,80),
    currency: String(order.currency || items[0]?.currency || "INR").slice(0,8),
    total_amount: Number(order.total_price ?? order.total_amount ?? order.grand_total ?? order.amount ?? order.total ?? 0) || 0,
    customer_name: String(customer.name || [customer.first_name,customer.last_name].filter(Boolean).join(" ") || order.buyer_name || "").slice(0,160),
    customer_email: String(customer.email || order.email || order.billing?.email || "").slice(0,254),
    customer_phone: String(customer.phone || order.phone || order.billing?.phone || "").slice(0,40),
    shipping_address: safeJson(order.shipping_address || order.shippingAddress || order.shipping || {}),
    ordered_at: String(created).slice(0,64), items
  };
}
async function hmacBase64(secret, rawText) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), {name:"HMAC",hash:"SHA-256"}, false, ["sign"]);
  const signature = await crypto.subtle.sign("HMAC", key, enc.encode(rawText));
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}
async function verifyProviderWebhook(request, channel, rawText, env) {
  if (channel.platform === "other" || channel.platform === "meesho" || channel.platform === "flipkart" ||
      channel.platform === "amazon_india" || channel.platform === "etsy" || channel.platform === "ebay") {
    const supplied = request.headers.get("X-RS-Channel-Secret") || "";
    return !!supplied && constantEqual(await hash(supplied), channel.webhook_secret_hash || "");
  }
  let credentials;
  try { credentials = await decryptCredentials(env, channel.credentials_ciphertext); } catch { return false; }
  if (channel.platform === "shopify") {
    const secret = String(credentials.webhook_secret || credentials.api_secret || "");
    const supplied = request.headers.get("X-Shopify-Hmac-Sha256") || "";
    if (!secret || !supplied) return false;
    return constantEqual(await hmacBase64(secret, rawText), supplied);
  }
  if (channel.platform === "woocommerce") {
    const secret = String(credentials.webhook_secret || "");
    const supplied = request.headers.get("X-WC-Webhook-Signature") || "";
    if (!secret || !supplied) return false;
    return constantEqual(await hmacBase64(secret, rawText), supplied);
  }
  return false;
}
async function saveMarketplaceOrder(db, channel, normalized, eventId) {
  const existing = await first(db,"SELECT id FROM marketplace_orders WHERE channel_id=? AND external_order_id=?",[channel.id,normalized.external_order_id]);
  const stamp = now();
  let orderId;
  if (existing) {
    orderId = existing.id;
    await db.prepare("UPDATE marketplace_orders SET external_status=?,currency=?,total_amount=?,customer_name=?,customer_email=?,customer_phone=?,shipping_address=?,ordered_at=?,updated_at=?,last_event_id=? WHERE id=?")
      .bind(normalized.external_status,normalized.currency,normalized.total_amount,normalized.customer_name,normalized.customer_email,normalized.customer_phone,normalized.shipping_address,normalized.ordered_at,stamp,eventId,orderId).run();
  } else {
    orderId = await insert(db,"marketplace_orders",{channel_id:channel.id,external_order_id:normalized.external_order_id,external_status:normalized.external_status,currency:normalized.currency,total_amount:normalized.total_amount,customer_name:normalized.customer_name,customer_email:normalized.customer_email,customer_phone:normalized.customer_phone,shipping_address:normalized.shipping_address,ordered_at:normalized.ordered_at,created_at:stamp,updated_at:stamp,last_event_id:eventId});
  }
  await db.prepare("DELETE FROM marketplace_order_items WHERE marketplace_order_id=?").bind(orderId).run();
  for (const item of normalized.items) await insert(db,"marketplace_order_items",{marketplace_order_id:orderId,...item,created_at:stamp});
  return orderId;
}

export async function handleSalesWebhook(request, env, path) {
  const match = /^\/api\/sales-channels\/(\d+)\/webhook$/.exec(path);
  if (!match || request.method !== "POST") return null;
  const id = Number(match[1]), channel = await first(env.DB,"SELECT * FROM sales_channels WHERE id=? AND status<>'disabled'",[id]);
  if (!channel) return new Response(JSON.stringify({error:"Unknown or disabled sales channel"}),{status:404,headers:{"Content-Type":"application/json"}});
  const rawText = await request.text();
  if (rawText.length > 1024*1024) return new Response(JSON.stringify({error:"Payload too large"}),{status:413});
  if (!await verifyProviderWebhook(request,channel,rawText,env)) return new Response(JSON.stringify({error:"Invalid webhook signature"}),{status:401,headers:{"Content-Type":"application/json"}});
  let payload; try { payload = JSON.parse(rawText); } catch { return new Response(JSON.stringify({error:"Invalid JSON"}),{status:400}); }
  const eventId = String(request.headers.get("X-Shopify-Webhook-Id") || request.headers.get("X-WC-Webhook-Delivery-ID") ||
    request.headers.get("X-Event-Id") || (payload && typeof payload==="object" ? payload.event_id || payload.id : "") || await hash(rawText)).slice(0,180);
  const eventType = String(request.headers.get("X-Shopify-Topic") || request.headers.get("X-WC-Webhook-Topic") ||
    request.headers.get("X-Event-Type") || (payload && typeof payload==="object" ? payload.event_type || payload.type : "") || "order.updated").slice(0,100);
  let duplicate = false;
  try {
    await insert(env.DB,"marketplace_events",{channel_id:id,external_event_id:eventId,event_type:eventType,payload_json:safeJson(payload),processing_status:"received",received_at:now()});
  } catch (error) {
    if (!/UNIQUE constraint failed/i.test(String(error))) throw error;
    duplicate = true;
  }
  const priorEvent = duplicate ? await first(env.DB,"SELECT id,processing_status FROM marketplace_events WHERE channel_id=? AND external_event_id=?",[id,eventId]) : null;
  if (duplicate && ["processed","accepted"].includes(String(priorEvent?.processing_status||""))) {
    return new Response(JSON.stringify({success:true,deduplicated:true}),{status:200,headers:{"Content-Type":"application/json"}});
  }
  if (duplicate) await env.DB.prepare("UPDATE marketplace_events SET processing_status='received' WHERE channel_id=? AND external_event_id=?").bind(id,eventId).run();
  let imported = false;
  if (/order|shipment|receipt/i.test(eventType) || (payload && typeof payload==="object" && (payload.order || payload.data?.order))) {
    const normalized = normalizeOrder(channel.platform,payload);
    const event = await first(env.DB,"SELECT id FROM marketplace_events WHERE channel_id=? AND external_event_id=?",[id,eventId]);
    await saveMarketplaceOrder(env.DB,channel,normalized,event?.id);
    await env.DB.prepare("UPDATE marketplace_events SET processing_status='processed' WHERE channel_id=? AND external_event_id=?").bind(id,eventId).run();
    await insert(env.DB,"sales_notifications",{channel_id:id,notification_type:"marketplace_order",title:"New marketplace order",message:channel.platform+" order "+normalized.external_order_id,created_at:now(),read_at:null});
    imported = true;
  } else {
    await env.DB.prepare("UPDATE marketplace_events SET processing_status='accepted' WHERE channel_id=? AND external_event_id=?").bind(id,eventId).run();
  }
  return new Response(JSON.stringify({success:true,imported}),{status:202,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}});
}
function constantEqual(a,b){if(a.length!==b.length)return false;let diff=0;for(let i=0;i<a.length;i++)diff|=a.charCodeAt(i)^b.charCodeAt(i);return diff===0;}

export async function handleSalesChannels(request, env, path, user) {
  const headers = {"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"};
  const admin = ["admin","developer"].includes(String(user?.role||"").toLowerCase());
  if (!admin) return new Response(JSON.stringify({detail:"Admin access required"}),{status:403,headers});
  if (path === "/api/sales-channels" && request.method === "GET") {
    const rows = await all(env.DB,"SELECT * FROM sales_channels ORDER BY platform,account_label");
    return new Response(JSON.stringify({channels:rows.map(publicChannel),platforms:PLATFORMS}),{status:200,headers});
  }
  if (path === "/api/sales-channels" && request.method === "POST") {
    const b = await request.json(), platform = String(b.platform||"").toLowerCase();
    if (!PLATFORMS[platform]) return new Response(JSON.stringify({detail:"Unsupported platform"}),{status:422,headers});
    const label = String(b.account_label||"").trim();
    if (!label || label.length>120) return new Response(JSON.stringify({detail:"Enter a seller account label (max 120 characters)"}),{status:422,headers});
    const creds = b.credentials && typeof b.credentials==="object" && !Array.isArray(b.credentials) ? b.credentials : {};
    const secret = randomToken();
    const encrypted = await encryptCredentials(env,creds);
    const id = await insert(env.DB,"sales_channels",{platform,account_label:label,status:"pending_authorization",auth_type:PLATFORMS[platform].auth,credentials_ciphertext:encrypted,webhook_secret_hash:await hash(secret),created_at:now(),updated_at:now(),last_sync_at:null,last_error:null});
    return new Response(JSON.stringify({success:true,channel_id:id,webhook_secret:secret,webhook_url_path:`/api/sales-channels/${id}/webhook`,message:"Save the webhook secret now; it is shown only once. Add marketplace API credentials through the secure Admin connection form, never in chat."}),{status:201,headers});
  }
  const credentialsMatch = /^\/api\/sales-channels\/(\d+)\/credentials$/.exec(path);
  if (credentialsMatch && request.method === "PUT") {
    const id=Number(credentialsMatch[1]), channel=await first(env.DB,"SELECT id FROM sales_channels WHERE id=?",[id]);
    if(!channel)return new Response(JSON.stringify({detail:"Channel not found"}),{status:404,headers});
    const b=await request.json(), credentials=b.credentials && typeof b.credentials==="object" && !Array.isArray(b.credentials)?b.credentials:null;
    if(!credentials)return new Response(JSON.stringify({detail:"Credentials must be a JSON object"}),{status:422,headers});
    const encrypted=await encryptCredentials(env,credentials);
    await env.DB.prepare("UPDATE sales_channels SET credentials_ciphertext=?,status='configured',last_error=NULL,updated_at=? WHERE id=?").bind(encrypted,now(),id).run();
    return new Response(JSON.stringify({success:true,status:"configured",secrets_exposed:false}),{status:200,headers});
  }
  const mappingMatch = /^\/api\/sales-channels\/(\d+)\/product-mappings$/.exec(path);
  if (mappingMatch && request.method === "GET") {
    return new Response(JSON.stringify(await all(env.DB,"SELECT m.*,p.name AS product_name,p.sku AS product_sku FROM channel_product_mappings m JOIN bt_products p ON p.id=m.product_id WHERE m.channel_id=? ORDER BY m.external_sku",[Number(mappingMatch[1])])),{status:200,headers});
  }
  if (mappingMatch && request.method === "POST") {
    const id=Number(mappingMatch[1]),b=await request.json(),sku=String(b.external_sku||"").trim(),productId=Number(b.product_id);
    const product=await first(env.DB,"SELECT id FROM bt_products WHERE id=?",[productId]);
    if(!sku||sku.length>160||!product)return new Response(JSON.stringify({detail:"A valid external SKU and existing Raw Strength product are required"}),{status:422,headers});
    const stamp=now();
    await env.DB.prepare("INSERT INTO channel_product_mappings(channel_id,external_listing_id,external_sku,product_id,mapping_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(channel_id,external_sku) DO UPDATE SET external_listing_id=excluded.external_listing_id,product_id=excluded.product_id,mapping_status='confirmed',updated_at=excluded.updated_at").bind(id,String(b.external_listing_id||""),sku,productId,"confirmed",stamp,stamp).run();
    return new Response(JSON.stringify({success:true}),{status:200,headers});
  }
  const webhook = /^\/api\/sales-channels\/(\d+)\/webhook-secret\/rotate$/.exec(path);
  if (webhook && request.method==="POST") {
    const secret=randomToken(); await env.DB.prepare("UPDATE sales_channels SET webhook_secret_hash=?,updated_at=? WHERE id=?").bind(await hash(secret),now(),Number(webhook[1])).run();
    return new Response(JSON.stringify({success:true,webhook_secret:secret}),{status:200,headers});
  }
  const channelMatch = /^\/api\/sales-channels\/(\d+)$/.exec(path);
  if (channelMatch && request.method==="DELETE") {
    await env.DB.prepare("UPDATE sales_channels SET status='disabled',credentials_ciphertext='',updated_at=? WHERE id=?").bind(now(),Number(channelMatch[1])).run();
    return new Response(JSON.stringify({success:true,disabled:true}),{status:200,headers});
  }
  if (path === "/api/sales-orders" && request.method === "GET") {
    const limit=Math.min(500,Math.max(1,Number(new URL(request.url).searchParams.get("limit")||100)));
    const orders=await all(env.DB,"SELECT o.*,c.platform,c.account_label FROM marketplace_orders o JOIN sales_channels c ON c.id=o.channel_id ORDER BY o.ordered_at DESC LIMIT ?",[limit]);
    return new Response(JSON.stringify(orders),{status:200,headers});
  }
  if (path === "/api/sales-notifications" && request.method === "GET") {
    return new Response(JSON.stringify(await all(env.DB,"SELECT n.*,c.platform,c.account_label FROM sales_notifications n LEFT JOIN sales_channels c ON c.id=n.channel_id ORDER BY n.created_at DESC LIMIT 100")),{status:200,headers});
  }
  const syncMatch=/^\/api\/sales-channels\/(\d+)\/sync$/.exec(path);
  if (syncMatch && request.method==="POST") {
    const id=Number(syncMatch[1]), channel=await first(env.DB,"SELECT * FROM sales_channels WHERE id=? AND status<>'disabled'",[id]);
    if(!channel)return new Response(JSON.stringify({detail:"Channel not found"}),{status:404,headers});
    const job=await insert(env.DB,"sales_sync_jobs",{channel_id:id,job_type:"order_import",status:"blocked_credentials",started_at:now(),finished_at:now(),error_message:"Live API polling is gated until the platform-specific seller app authorization and endpoint credentials are configured. Webhook/import ingestion is ready."});
    return new Response(JSON.stringify({success:false,job_id:job,status:"blocked_credentials",message:"The channel framework is connected, but live API polling requires approved seller API credentials and authorization. Incoming signed webhook orders are imported automatically."}),{status:409,headers});
  }
  return new Response(JSON.stringify({error:"Not found"}),{status:404,headers});
}
