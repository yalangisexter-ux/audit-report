import test from "node:test";
import assert from "node:assert/strict";
import { handleSalesChannels, handleSalesWebhook } from "../src/sales-channels.js";
function fakeDb(){const rows={channels:[],orders:[],items:[],events:[],notifications:[],jobs:[],mappings:[]};let id=0;return{rows,prepare(sql){let args=[];return{bind(...v){args=v;return{async first(){if(sql.includes("FROM sales_channels WHERE id=?"))return rows.channels.find(x=>x.id===args[0])||null;if(sql.includes("FROM marketplace_orders WHERE channel_id=?"))return rows.orders.find(x=>x.channel_id===args[0]&&x.external_order_id===args[1])||null;if(sql.includes("FROM marketplace_events WHERE channel_id=?"))return rows.events.find(x=>x.channel_id===args[0]&&x.external_event_id===args[1])||null;if(sql.includes("FROM bt_products"))return args[0]===7?{id:7}:null;return null;},async all(){if(sql.includes("FROM sales_channels"))return{results:rows.channels};if(sql.includes("FROM marketplace_orders"))return{results:rows.orders};if(sql.includes("FROM sales_notifications"))return{results:rows.notifications};if(sql.includes("FROM channel_product_mappings"))return{results:rows.mappings};return{results:[]};},async run(){if(sql.startsWith("INSERT INTO sales_channels")){rows.channels.push({id:++id,platform:args[0],account_label:args[1],status:args[2],auth_type:args[3],credentials_ciphertext:args[4],webhook_secret_hash:args[5],created_at:args[6],updated_at:args[7]});return{success:true,meta:{last_row_id:id,changes:1}};}if(sql.startsWith("INSERT INTO marketplace_events")){rows.events.push({id:++id,channel_id:args[0],external_event_id:args[1],event_type:args[2],payload_json:args[3],processing_status:args[4],received_at:args[5]});return{success:true,meta:{last_row_id:id,changes:1}};}if(sql.startsWith("INSERT INTO marketplace_orders")){rows.orders.push({id:++id,channel_id:args[0],external_order_id:args[1],external_status:args[2],currency:args[3],total_amount:args[4],customer_name:args[5],customer_email:args[6],customer_phone:args[7],shipping_address:args[8],ordered_at:args[9],created_at:args[10],updated_at:args[11],last_event_id:args[12]});return{success:true,meta:{last_row_id:id,changes:1}};}if(sql.startsWith("INSERT INTO marketplace_order_items")){rows.items.push(args);return{success:true,meta:{last_row_id:++id,changes:1}};}if(sql.startsWith("INSERT INTO sales_notifications")){rows.notifications.push(args);return{success:true,meta:{last_row_id:++id,changes:1}};}return{success:true,meta:{changes:1,last_row_id:++id}};}};}};}};}
const env={DB:fakeDb(),CONNECTOR_ENCRYPTION_KEY:"ab".repeat(32)},admin={id:1,username:"Admin",role:"Admin"};
const req=(url,method="GET",body,headers={})=>new Request("https://api.test"+url,{method,headers:{"Content-Type":"application/json",...headers},...(body===undefined?{}:{body:JSON.stringify(body)})});
test("channel creation encrypts credentials and only returns one-time webhook secret",async()=>{const r=await handleSalesChannels(req("/api/sales-channels","POST",{platform:"shopify",account_label:"Main Shopify",credentials:{access_token:"top-secret"}}),env,"/api/sales-channels",admin);assert.equal(r.status,201);const b=await r.json();assert.ok(b.webhook_secret);assert.ok(!JSON.stringify(b).includes("top-secret"));assert.ok(!env.DB.rows.channels[0].credentials_ciphertext.includes("top-secret"));});
test("webhook rejects missing secret and imports a marketplace order",async()=>{const r=await handleSalesChannels(req("/api/sales-channels","POST",{platform:"other",account_label:"Partner feed",credentials:{}}),env,"/api/sales-channels",admin);const c=await r.json();const payload={event_id:"evt-1",event_type:"order.created",order:{id:"ORDER-100",status:"paid",total_amount:250,currency:"INR",items:[{sku:"RS-01",name:"Training kit",quantity:2,price:125}]}};const denied=await handleSalesWebhook(req("/api/sales-channels/"+c.channel_id+"/webhook","POST",payload),env,"/api/sales-channels/"+c.channel_id+"/webhook");assert.equal(denied.status,401);const accepted=await handleSalesWebhook(req("/api/sales-channels/"+c.channel_id+"/webhook","POST",payload,{"X-RS-Channel-Secret":c.webhook_secret}),env,"/api/sales-channels/"+c.channel_id+"/webhook");assert.equal(accepted.status,202);assert.equal((await accepted.json()).imported,true);assert.equal(env.DB.rows.orders[0].external_order_id,"ORDER-100");assert.equal(env.DB.rows.items.length,1);});
test("unsupported sales platform is rejected",async()=>{const r=await handleSalesChannels(req("/api/sales-channels","POST",{platform:"random",account_label:"x"}),env,"/api/sales-channels",admin);assert.equal(r.status,422);});

async function signWebhook(secret, body) {
  const key=await crypto.subtle.importKey("raw",new TextEncoder().encode(secret),{name:"HMAC",hash:"SHA-256"},false,["sign"]);
  const sig=await crypto.subtle.sign("HMAC",key,new TextEncoder().encode(body));
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}
test("Shopify native webhook HMAC authenticates and imports the order",async()=>{
  const secret="shopify-webhook-secret";
  const created=await handleSalesChannels(req("/api/sales-channels","POST",{platform:"shopify",account_label:"Shopify live",credentials:{webhook_secret:secret}}),env,"/api/sales-channels",admin);
  const channel=await created.json();
  const body=JSON.stringify({id:98765,name:"#1001",financial_status:"paid",total_price:"1499.00",currency:"INR",created_at:"2026-11-12T09:00:00Z",customer:{first_name:"Test",last_name:"Buyer",email:"buyer@example.test"},line_items:[{id:1,sku:"RS-TSHIRT",title:"Raw Strength Tee",quantity:2,price:"749.50"}]});
  const signature=await signWebhook(secret,body);
  const response=await handleSalesWebhook(new Request("https://api.test/api/sales-channels/"+channel.channel_id+"/webhook",{method:"POST",headers:{"Content-Type":"application/json","X-Shopify-Hmac-Sha256":signature,"X-Shopify-Webhook-Id":"shopify-delivery-1","X-Shopify-Topic":"orders/create"},body}),env,"/api/sales-channels/"+channel.channel_id+"/webhook");
  assert.equal(response.status,202);
  const order=env.DB.rows.orders.find(x=>x.external_order_id==="98765");
  assert.equal(order.total_amount,1499);
  assert.equal(order.customer_email,"buyer@example.test");
  assert.equal(env.DB.rows.items.at(-1)[5],"RS-TSHIRT");
});
test("WooCommerce native webhook signature and order fields are supported",async()=>{
  const secret="woocommerce-webhook-secret";
  const created=await handleSalesChannels(req("/api/sales-channels","POST",{platform:"woocommerce",account_label:"Woo store",credentials:{webhook_secret:secret}}),env,"/api/sales-channels",admin);
  const channel=await created.json();
  const body=JSON.stringify({id:4455,status:"processing",total:"825.00",currency:"INR",date_created:"2026-11-12T09:30:00",billing:{first_name:"Woo",last_name:"Buyer",email:"woo@example.test",phone:"9999999999"},shipping:{address_1:"Main Road"},line_items:[{id:8,sku:"RS-BAND",name:"Resistance Band",quantity:3,price:275}]});
  const signature=await signWebhook(secret,body);
  const response=await handleSalesWebhook(new Request("https://api.test/api/sales-channels/"+channel.channel_id+"/webhook",{method:"POST",headers:{"Content-Type":"application/json","X-WC-Webhook-Signature":signature,"X-WC-Webhook-Delivery-ID":"woo-delivery-1","X-WC-Webhook-Topic":"order.created"},body}),env,"/api/sales-channels/"+channel.channel_id+"/webhook");
  assert.equal(response.status,202);
  const order=env.DB.rows.orders.find(x=>x.external_order_id==="4455");
  assert.equal(order.total_amount,825);
  assert.equal(order.customer_name,"Woo Buyer");
  assert.equal(order.customer_phone,"9999999999");
});
test("Shopify webhook rejects an invalid HMAC",async()=>{
  const created=await handleSalesChannels(req("/api/sales-channels","POST",{platform:"shopify",account_label:"Bad signature test",credentials:{webhook_secret:"right-secret"}}),env,"/api/sales-channels",admin);
  const channel=await created.json(),body=JSON.stringify({id:123,event_type:"order.created"});
  const response=await handleSalesWebhook(new Request("https://api.test/api/sales-channels/"+channel.channel_id+"/webhook",{method:"POST",headers:{"Content-Type":"application/json","X-Shopify-Hmac-Sha256":"invalid","X-Shopify-Webhook-Id":"bad-signature"},body}),env,"/api/sales-channels/"+channel.channel_id+"/webhook");
  assert.equal(response.status,401);
});
