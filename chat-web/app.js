(() => {
  "use strict";
  const state = { token: "", user: null, conversations: [], users: [], activeId: "", activeConversation: null, messages: new Map(), socket: null, epoch: 0, reconnectTimer: null, retry: 0, pendingAction: null, workers: [], peers: new Set(), peerConnections: new Map(), localShareStream: null, pendingShareOffer: null, remoteShareActive: false, iceQueues: new Map() };
  const $ = id => document.getElementById(id);
  const base = window.location.origin.replace(/\/+$/u, "");
  function setError(id, message) { $(id).textContent = message || ""; }
  function escapeTime(value) { try { return new Date(value).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}); } catch { return ""; } }
  function api(path, options = {}) {
    const headers = {"Content-Type":"application/json", ...(options.headers || {})};
    if (state.token) headers.Authorization = "Bearer " + state.token;
    return fetch(base + path, {...options, headers, cache:"no-store"}).then(async response => {
      let data = {};
      try { data = await response.json(); } catch {}
      if (!response.ok) throw new Error(data.error || "Request failed (" + response.status + ").");
      return data;
    });
  }
  function setStatus(text, mode = "") {
    $("sidebarStatus").textContent = text;
    $("sidebarStatus").className = "status " + mode;
  }
  function stopSocket() {
    state.epoch++;
    if (state.reconnectTimer) clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
    if (state.socket) {
      const old = state.socket;
      state.socket = null;
      old.onclose = null;
      try { old.close(1000, "Conversation changed"); } catch {}
    }
  }
  function renderConversations() {
    const list = $("conversationList");
    list.replaceChildren();
    if (!state.conversations.length) {
      const p = document.createElement("p"); p.className = "muted"; p.textContent = "No conversations yet. Start a private chat or create a group."; list.append(p); return;
    }
    for (const conversation of state.conversations) {
      const button = document.createElement("button");
      button.className = "conv" + (conversation.id === state.activeId ? " active" : "");
      const title = document.createElement("strong"); title.textContent = conversation.title || conversation.name || "Conversation";
      const preview = document.createElement("small"); preview.textContent = conversation.last_message || (conversation.kind === "group" ? "Team group" : "Private conversation");
      button.append(title, preview);
      button.addEventListener("click", () => { $("sidebar").classList.remove("open"); openConversation(conversation.id); });
      list.append(button);
    }
  }
  function renderMessages() {
    const root = $("messages");
    root.replaceChildren();
    const rows = Array.from(state.messages.values()).sort((a,b) => Number(a.id)-Number(b.id));
    if (!rows.length) {
      const empty = document.createElement("div"); empty.className = "empty";
      const big = document.createElement("div"); big.className = "big"; big.textContent = "✦";
      const strong = document.createElement("strong"); strong.textContent = "Start the conversation";
      const p = document.createElement("p"); p.textContent = "Messages are saved and delivered only to authorized members of this conversation.";
      empty.append(big,strong,p); root.append(empty); return;
    }
    for (const message of rows) {
      const bubble = document.createElement("article");
      bubble.className = "message" + (Number(message.sender_user_id) === Number(state.user.id) ? " mine" : "");
      const meta = document.createElement("div"); meta.className = "message-meta";
      const name = document.createElement("strong"); name.textContent = message.display_name || message.username || "Employee";
      const time = document.createElement("span"); time.textContent = escapeTime(message.created_at);
      meta.append(name,time);
      const body = document.createElement("div"); body.className = "message-body"; body.textContent = message.text || "";
      bubble.append(meta,body); root.append(bubble);
    }
    root.scrollTop = root.scrollHeight;
  }
  async function loadConversations(preferredId = "") {
    const data = await api("/api/conversations");
    state.conversations = data.conversations || [];
    renderConversations();
    const desired = preferredId || state.activeId;
    if (desired && state.conversations.some(c => c.id === desired)) {
      if (state.activeId !== desired) await openConversation(desired);
    } else if (state.conversations.length) {
      await openConversation(state.conversations[0].id);
    } else {
      stopScreenShare(); for (const id of state.peerConnections.keys()) closePeer(id); state.peers.clear(); state.pendingShareOffer = null; renderShareControls(); stopSocket(); state.activeId = ""; state.activeConversation = null; state.messages.clear();
      $("conversationTitle").textContent = "No conversations yet";
      $("messages").innerHTML = '<div class="empty"><div class="big">✦</div><strong>Start a private chat or create a group</strong></div>';
      $("messageInput").disabled = true; $("sendBtn").disabled = true;
    }
  }
  async function loadHistory(conversationId) {
    const data = await api("/api/conversations/" + encodeURIComponent(conversationId) + "/messages?limit=100");
    if (state.activeId !== conversationId) return;
    for (const message of data.messages || []) state.messages.set(Number(message.id), message);
    renderMessages();
  }
  function sendSignal(targetUserId, signal) {
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return;
    state.socket.send(JSON.stringify({type:"rtc-signal", targetUserId:Number(targetUserId), signal}));
  }
  function setShareStatus(message) { $("shareStatus").textContent = message; }
  function renderShareControls() {
    const panel = $("sharePanel");
    panel.classList.toggle("hidden", !state.user || !state.activeConversation);
    $("startShareBtn").classList.toggle("hidden", !!state.localShareStream || state.remoteShareActive);
    $("stopShareBtn").classList.toggle("hidden", !state.localShareStream);
    $("acceptShareBtn").classList.toggle("hidden", !state.pendingShareOffer);
    $("declineShareBtn").classList.toggle("hidden", !state.pendingShareOffer);
    const visibleVideos = !!state.localShareStream || state.remoteShareActive;
    $("shareVideos").classList.toggle("hidden", !visibleVideos);
    $("localShareWrap").classList.toggle("hidden", !state.localShareStream);
    $("remoteShareWrap").classList.toggle("hidden", !state.remoteShareActive);
  }
  function closePeer(userId) {
    const id = Number(userId);
    const pc = state.peerConnections.get(id);
    if (pc) { try { pc.close(); } catch {} state.peerConnections.delete(id); }
    state.iceQueues.delete(id);
    if (state.pendingShareOffer && Number(state.pendingShareOffer.fromUserId) === id) state.pendingShareOffer = null;
    if (state.remoteShareActive && Number($("remoteShareVideo").dataset.peerId) === id) {
      $("remoteShareVideo").srcObject = null;
      $("remoteShareVideo").dataset.peerId = "";
      state.remoteShareActive = false;
      $("remoteShareLabel").textContent = "Employee · shared screen";
      setShareStatus("The other participant stopped sharing.");
    }
    renderShareControls();
  }
  function makePeerConnection(userId) {
    const id = Number(userId);
    if (state.peerConnections.has(id)) return state.peerConnections.get(id);
    const pc = new RTCPeerConnection({iceServers:[{urls:"stun:stun.l.google.com:19302"},{urls:"stun:stun1.l.google.com:19302"}]});
    state.peerConnections.set(id, pc);
    pc.onicecandidate = event => { if (event.candidate) sendSignal(id,{kind:"ice",candidate:event.candidate.toJSON()}); };
    pc.ontrack = event => {
      const stream = event.streams && event.streams[0];
      if (!stream) return;
      $("remoteShareVideo").srcObject = stream;
      $("remoteShareVideo").dataset.peerId = String(id);
      $("remoteShareLabel").textContent = (state.pendingShareOffer?.displayName || "Employee") + " · shared screen";
      state.remoteShareActive = true;
      setShareStatus("Viewing a live screen share. The other participant controls when it ends.");
      renderShareControls();
      $("remoteShareVideo").play().catch(()=>{});
    };
    pc.onconnectionstatechange = () => {
      if (["failed","closed"].includes(pc.connectionState)) closePeer(id);
      else if (pc.connectionState === "connected") setShareStatus("Screen sharing connected · peer-to-peer");
    };
    if (state.localShareStream) {
      for (const track of state.localShareStream.getTracks()) pc.addTrack(track,state.localShareStream);
    }
    return pc;
  }
  async function startScreenShare() {
    if (!state.activeConversation || !state.socket || state.socket.readyState !== WebSocket.OPEN) {
      setShareStatus("Connect to a conversation before sharing."); return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      setShareStatus("Screen sharing requires a supported browser over HTTPS."); return;
    }
    if (state.remoteShareActive) { setShareStatus("Stop viewing the current share before starting yours."); return; }
    if (!state.peers.size) { setShareStatus("No other conversation members are online to receive the share."); return; }
    try {
      state.localShareStream = await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:12,max:20}},audio:false});
      $("localShareVideo").srcObject = state.localShareStream;
      $("localShareVideo").play().catch(()=>{});
      state.localShareStream.getVideoTracks()[0].addEventListener("ended", stopScreenShare, {once:true});
      setShareStatus("Sharing your screen with online conversation members. Use Stop sharing to end.");
      renderShareControls();
      for (const peerId of state.peers) await sendShareOffer(peerId);
    } catch (error) {
      if (error && error.name === "NotAllowedError") setShareStatus("Screen sharing was cancelled or permission was denied.");
      else setShareStatus("Unable to start screen sharing: " + (error?.message || "unknown error"));
      state.localShareStream = null; renderShareControls();
    }
  }
  async function sendShareOffer(peerId) {
    if (!state.localShareStream || !state.peers.has(Number(peerId))) return;
    const pc = makePeerConnection(peerId);
    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      sendSignal(peerId,{kind:"offer",description:pc.localDescription});
    } catch (error) { setShareStatus("Could not connect to a participant: " + (error?.message || "connection error")); }
  }
  function stopScreenShare() {
    if (state.localShareStream) {
      const stream = state.localShareStream;
      state.localShareStream = null;
      for (const track of stream.getTracks()) track.stop();
      for (const peerId of state.peers) sendSignal(peerId,{kind:"end"});
      for (const [id,pc] of state.peerConnections) { try { pc.close(); } catch {} state.peerConnections.delete(id); }
      $("localShareVideo").srcObject = null;
      setShareStatus("You stopped sharing your screen.");
      renderShareControls();
    }
  }
  async function acceptIncomingShare() {
    const pending = state.pendingShareOffer;
    if (!pending || !state.peers.has(Number(pending.fromUserId))) return;
    const id = Number(pending.fromUserId);
    try {
      const pc = makePeerConnection(id);
      await pc.setRemoteDescription(new RTCSessionDescription(pending.description));
      const queued = state.iceQueues.get(id) || [];
      for (const candidate of queued) await pc.addIceCandidate(new RTCIceCandidate(candidate)).catch(()=>{});
      state.iceQueues.delete(id);
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      sendSignal(id,{kind:"answer",description:pc.localDescription});
      state.pendingShareOffer = null;
      setShareStatus("Connecting to " + (pending.displayName || "the participant") + "…");
      renderShareControls();
    } catch (error) { setShareStatus("Could not accept the screen share: " + (error?.message || "connection error")); }
  }
  function declineIncomingShare() {
    const pending = state.pendingShareOffer;
    if (pending) sendSignal(pending.fromUserId,{kind:"reject"});
    if (pending) closePeer(pending.fromUserId);
    state.pendingShareOffer = null;
    setShareStatus("Incoming screen share declined.");
    renderShareControls();
  }
  async function handleRtcSignal(packet) {
    const fromId = Number(packet.fromUserId);
    if (!fromId || fromId === Number(state.user?.id) || !state.activeConversation) return;
    const signal = packet.signal || {};
    if (signal.kind === "offer") {
      if (state.localShareStream || state.remoteShareActive || state.pendingShareOffer) {
        sendSignal(fromId,{kind:"busy"});
        return;
      }
      state.pendingShareOffer = {fromUserId:fromId,displayName:packet.fromDisplayName || "Employee",description:signal.description};
      setShareStatus((packet.fromDisplayName || "A participant") + " wants to share their screen. Accept only if you trust them.");
      renderShareControls();
      return;
    }
    if (signal.kind === "reject") { closePeer(fromId); setShareStatus("A participant declined the screen share."); return; }
    if (signal.kind === "busy") { setShareStatus("A participant is already in another screen-share session."); closePeer(fromId); return; }
    if (signal.kind === "end") { closePeer(fromId); return; }
    const pc = state.peerConnections.get(fromId);
    if (signal.kind === "answer" && pc) {
      await pc.setRemoteDescription(new RTCSessionDescription(signal.description));
      const queued = state.iceQueues.get(fromId) || [];
      for (const candidate of queued) await pc.addIceCandidate(new RTCIceCandidate(candidate)).catch(()=>{});
      state.iceQueues.delete(fromId);
    } else if (signal.kind === "ice") {
      if (pc && pc.remoteDescription) await pc.addIceCandidate(new RTCIceCandidate(signal.candidate)).catch(()=>{});
      else {
        const queue = state.iceQueues.get(fromId) || [];
        if (queue.length < 64) queue.push(signal.candidate);
        state.iceQueues.set(fromId,queue);
      }
    }
  }
  function handlePeerPacket(packet) {
    const id = Number(packet.userId);
    if (!id || id === Number(state.user?.id)) return;
    if (packet.type === "peer-joined") {
      state.peers.add(id);
      if (state.localShareStream) sendShareOffer(id);
    } else if (packet.type === "peer-left") {
      state.peers.delete(id); closePeer(id);
    } else if (packet.type === "peers") {
      state.peers = new Set((packet.peers || []).map(Number).filter(value => value && value !== Number(state.user?.id)));
    }
  }
  async function connectSocket(conversationId, epoch) {
    if (epoch !== state.epoch || state.activeId !== conversationId) return;
    try {
      const ticketData = await api("/api/chat/ticket", {method:"POST", body:JSON.stringify({conversationId})});
      if (epoch !== state.epoch) return;
      const wsUrl = base.replace(/^https:/u,"wss:").replace(/^http:/u,"ws:") + "/api/chat/ws?ticket=" + encodeURIComponent(ticketData.ticket);
      const socket = new WebSocket(wsUrl);
      state.socket = socket;
      socket.onopen = () => {
        if (epoch !== state.epoch) { socket.close(); return; }
        state.retry = 0; setStatus("Live · connected", "online");
        $("messageInput").disabled = false; $("sendBtn").disabled = false;
        loadHistory(conversationId).catch(error => setStatus(error.message, "offline"));
      };
      socket.onmessage = event => {
        if (epoch !== state.epoch) return;
        try {
          const packet = JSON.parse(event.data);
          if (packet.type === "message" && packet.message) {
            state.messages.set(Number(packet.message.id), packet.message);
            renderMessages();
            const conv = state.conversations.find(c => c.id === conversationId);
            if (conv) { conv.last_message = packet.message.text; conv.last_message_at = packet.message.created_at; renderConversations(); }
          } else if (["peers","peer-joined","peer-left"].includes(packet.type)) {
            handlePeerPacket(packet);
          } else if (packet.type === "rtc-signal") {
            handleRtcSignal(packet).catch(error => setShareStatus("Screen share signaling error: " + (error?.message || "unknown error")));
          } else if (packet.type === "error") setStatus(packet.message || "Chat error", "offline");
        } catch {}
      };
      socket.onerror = () => setStatus("Connection issue · reconnecting", "offline");
      socket.onclose = () => {
        if (epoch !== state.epoch) return;
        state.socket = null; $("messageInput").disabled = true; $("sendBtn").disabled = true;
        setStatus("Disconnected · reconnecting", "offline");
        const delay = Math.min(30000, 1000 * Math.pow(2, Math.min(state.retry++, 5)));
        state.reconnectTimer = setTimeout(async () => {
          if (epoch !== state.epoch) return;
          try { await loadHistory(conversationId); } catch {}
          connectSocket(conversationId, epoch);
        }, delay);
      };
    } catch (error) {
      if (epoch !== state.epoch) return;
      setStatus(error.message + " · retrying", "offline");
      const delay = Math.min(30000, 1000 * Math.pow(2, Math.min(state.retry++, 5)));
      state.reconnectTimer = setTimeout(() => connectSocket(conversationId, epoch), delay);
    }
  }
  async function openConversation(id) {
    const conversation = state.conversations.find(c => c.id === id);
    if (!conversation) return;
    stopScreenShare(); for (const peerId of state.peerConnections.keys()) closePeer(peerId); state.peers.clear(); state.pendingShareOffer = null; state.remoteShareActive = false; renderShareControls();
    stopSocket(); const epoch = state.epoch;
    state.activeId = id; state.activeConversation = conversation; state.messages.clear(); state.retry = 0;
    $("conversationTitle").textContent = conversation.title || conversation.name || "Conversation";
    $("conversationSubtitle").textContent = conversation.kind === "group" ? "Authorized group · Message history is saved" : "Private conversation · Only the two members can read messages";
    $("addMemberBtn").classList.toggle("hidden", !(conversation.kind === "group" && (conversation.member_role === "owner" || state.user.role === "Admin")));
    $("messageInput").disabled = true; $("sendBtn").disabled = true;
    renderConversations(); renderMessages(); setStatus("Loading history…");
    try { await loadHistory(id); } catch (error) { setStatus(error.message, "offline"); }
    connectSocket(id, epoch); renderShareControls();
  }
  function showDialog(title, fields, action) {
    $("dialogTitle").textContent = title; $("dialogFields").replaceChildren(); setError("dialogError", "");
    for (const field of fields) {
      const wrap = document.createElement("div"); wrap.className = "field";
      const label = document.createElement("label"); label.textContent = field.label; label.htmlFor = field.id;
      let input;
      if (field.options) {
        input = document.createElement("select");
        for (const option of field.options) { const opt = document.createElement("option"); opt.value = option.value; opt.textContent = option.label; input.append(opt); }
      } else {
        input = document.createElement("input"); input.type = field.type || "text"; input.autocomplete = field.autocomplete || "off";
      }
      input.id = field.id; input.required = field.required !== false;
      if (field.placeholder) input.placeholder = field.placeholder;
      if (field.maxLength) input.maxLength = field.maxLength;
      wrap.append(label,input); $("dialogFields").append(wrap);
    }
    state.pendingAction = action; $("dialog").classList.remove("hidden");
    const first = $("dialogFields").querySelector("input,select"); if (first) first.focus();
  }
  function hideDialog() { $("dialog").classList.add("hidden"); state.pendingAction = null; }
  $("dialogCancel").addEventListener("click", hideDialog);
  $("dialogForm").addEventListener("submit", async event => {
    event.preventDefault(); if (!state.pendingAction) return;
    const values = {}; for (const field of $("dialogFields").querySelectorAll("input,select")) values[field.id] = field.value;
    try { await state.pendingAction(values); hideDialog(); } catch (error) { setError("dialogError", error.message); }
  });
  $("loginForm").addEventListener("submit", async event => {
    event.preventDefault(); setError("loginError", "");
    const button = $("loginForm").querySelector("button[type=submit]"); button.disabled = true; button.textContent = "Signing in…";
    try {
      const data = await api("/api/auth/login", {method:"POST",body:JSON.stringify({username:$("username").value,password:$("password").value})});
      state.token = data.token; state.user = data.user;
      $("loginView").classList.add("hidden"); $("appView").classList.remove("hidden");
      $("signedInAs").textContent = (state.user.displayName || state.user.username) + " · " + state.user.role;
      $("adminPanel").classList.toggle("hidden", state.user.role !== "Admin");
      $("password").value = "";
      const directory = await api("/api/users"); state.users = directory.users || [];
      await loadConversations();
    } catch (error) { setError("loginError", error.message); }
    finally { button.disabled = false; button.textContent = "Sign in securely"; }
  });
  $("changePasswordBtn").addEventListener("click", () => {
    showDialog("Change chat password", [
      {id:"currentPassword",label:"Current password",type:"password",maxLength:256},
      {id:"newPassword",label:"New password (10+ characters, letters and numbers)",type:"password",maxLength:256}
    ], async values => {
      await api("/api/auth/password",{method:"POST",body:JSON.stringify({currentPassword:values.currentPassword,newPassword:values.newPassword})});
      alert("Password changed successfully.");
    });
  });
  $("logoutBtn").addEventListener("click", () => {
    stopSocket(); state.token = ""; state.user = null; state.conversations = []; state.users = []; state.activeId = "";
    $("appView").classList.add("hidden"); $("loginView").classList.remove("hidden"); $("password").value = ""; $("username").focus();
  });
  $("newPrivateBtn").addEventListener("click", () => {
    showDialog("Start a private chat", [{id:"username",label:"Employee username",placeholder:"e.g. taruna"}], async values => {
      const data = await api("/api/conversations/private",{method:"POST",body:JSON.stringify({username:values.username})});
      await loadConversations(data.conversationId);
    });
  });
  $("newGroupBtn").addEventListener("click", () => {
    showDialog("Create an authorized group", [
      {id:"groupName",label:"Group name",placeholder:"e.g. Operations"},
      {id:"members",label:"Member usernames (comma-separated)",placeholder:"taruna, siri, gopi",required:false}
    ], async values => {
      const usernames = values.members.split(",").map(value => value.trim()).filter(Boolean);
      const data = await api("/api/conversations/group",{method:"POST",body:JSON.stringify({name:values.groupName,usernames})});
      await loadConversations(data.conversationId);
    });
  });
  $("createUserBtn").addEventListener("click", () => {
    showDialog("Create chat account", [
      {id:"newUsername",label:"Username",placeholder:"employee.username",maxLength:40},
      {id:"displayName",label:"Display name",placeholder:"Employee name",maxLength:80},
      {id:"newPassword",label:"Temporary password (10+ characters)",type:"password",maxLength:256},
      {id:"role",label:"Role",options:[{value:"HR",label:"Employee / HR"},{value:"Admin",label:"Chat Admin"}]}
    ], async values => {
      await api("/api/admin/users",{method:"POST",body:JSON.stringify({username:values.newUsername,displayName:values.displayName,password:values.newPassword,role:values.role})});
      const directory = await api("/api/users"); state.users = directory.users || [];
      alert("Chat account created. Share the temporary password securely and ask the employee to change it after sign-in.");
    });
  });
  $("addMemberBtn").addEventListener("click", () => {
    const conversation = state.activeConversation; if (!conversation) return;
    showDialog("Add member to group", [{id:"memberUsername",label:"Existing chat username",placeholder:"employee.username"}], async values => {
      await api("/api/conversations/" + encodeURIComponent(conversation.id) + "/members",{method:"POST",body:JSON.stringify({username:values.memberUsername})});
      alert("Member added to the group.");
    });
  });
  $("composer").addEventListener("submit", event => {
    event.preventDefault(); const text = $("messageInput").value.trim();
    if (!text || !state.socket || state.socket.readyState !== WebSocket.OPEN) return;
    const clientMessageId = crypto.randomUUID();
    try {
      state.socket.send(JSON.stringify({type:"message",text,clientMessageId}));
      $("messageInput").value = "";
    } catch { setStatus("Message not sent · reconnecting", "offline"); }
  });
  $("startShareBtn").addEventListener("click", startScreenShare);
  $("stopShareBtn").addEventListener("click", stopScreenShare);
  $("acceptShareBtn").addEventListener("click", () => acceptIncomingShare().catch(error => setShareStatus(error.message)));
  $("declineShareBtn").addEventListener("click", declineIncomingShare);
  $("mobileMenuBtn").addEventListener("click", () => $("sidebar").classList.toggle("open"));
  window.addEventListener("online", () => { if (state.activeId && state.user && (!state.socket || state.socket.readyState > WebSocket.OPEN)) openConversation(state.activeId); });
  window.setInterval(() => { if (state.token) loadConversations().catch(error => setStatus(error.message, "offline")); }, 15000);
  window.addEventListener("beforeunload", () => { stopScreenShare(); for (const id of state.peerConnections.keys()) closePeer(id); stopSocket(); });
})();
