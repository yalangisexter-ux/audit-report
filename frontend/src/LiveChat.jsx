import React, { useState } from 'react';

const DEFAULT_CHAT_URL = 'https://raw-strength-employee-chat.yalangisexter.workers.dev';

function resolveChatUrl() {
  const configured = String(import.meta.env.VITE_CHAT_WORKER_URL || DEFAULT_CHAT_URL).trim();
  try {
    const url = new URL(configured);
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || !['', '/'].includes(url.pathname)) {
      return DEFAULT_CHAT_URL;
    }
    return url.origin;
  } catch {
    return DEFAULT_CHAT_URL;
  }
}

const CHAT_URL = resolveChatUrl();

export default function LiveChat() {
  const [frameKey, setFrameKey] = useState(0);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-slate-950/70 p-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-white">Private conversations and team groups</h3>
          <p className="mt-1 text-xs text-slate-400">
            Chat accounts are managed separately from Employee Audit Manager accounts. Your audit login is not shared with the chat service.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            type="button"
            className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-white/5"
            onClick={() => setFrameKey(value => value + 1)}
          >
            Reload chat
          </button>
          <a
            className="rounded-lg bg-cyan-400 px-3 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300"
            href={CHAT_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open in new tab ↗
          </a>
        </div>
      </div>
      <iframe
        key={frameKey}
        title="Raw Strength private and group Live Chat"
        src={CHAT_URL + '/'}
        loading="lazy"
        referrerPolicy="no-referrer"
        allow="camera; microphone; display-capture; fullscreen"
        allowFullScreen
        className="h-[78vh] min-h-[620px] w-full rounded-xl border border-white/10 bg-slate-950"
      />
      <p className="text-xs text-slate-500">
        Audio/video calls and screen sharing require HTTPS and browser permission. Use the chat service sign-in inside this panel; membership and message access are enforced by the chat service.
      </p>
    </div>
  );
}
