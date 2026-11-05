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

export default function LiveChat({ messages = [], user, onSendGeneral }) {
  const [mode, setMode] = useState('private');
  const [frameKey, setFrameKey] = useState(0);
  const [generalDraft, setGeneralDraft] = useState('');
  const [generalBusy, setGeneralBusy] = useState(false);
  const [generalError, setGeneralError] = useState('');

  const sendGeneralMessage = async event => {
    event.preventDefault();
    const content = generalDraft.trim();
    if (!content || generalBusy || typeof onSendGeneral !== 'function') return;
    setGeneralBusy(true);
    setGeneralError('');
    try {
      await onSendGeneral(content);
      setGeneralDraft('');
    } catch (error) {
      setGeneralError(error?.message || 'The general-channel message could not be sent.');
    } finally {
      setGeneralBusy(false);
    }
  };

  const tabButton = active =>
    'rounded-lg border px-3 py-2 text-xs font-semibold ' +
    (active
      ? 'border-cyan-300 bg-cyan-300 text-slate-950'
      : 'border-white/10 text-slate-300 hover:bg-white/5');

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-slate-950/70 p-3">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Live Chat mode">
          <button type="button" role="tab" aria-selected={mode === 'private'} className={tabButton(mode === 'private')} onClick={() => setMode('private')}>
            Private &amp; Group
          </button>
          <button type="button" role="tab" aria-selected={mode === 'general'} className={tabButton(mode === 'general')} onClick={() => setMode('general')}>
            General Channel
          </button>
        </div>
        {mode === 'private' && (
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
        )}
      </div>

      {mode === 'private' ? (
        <div className="space-y-3">
          <div className="rounded-xl border border-white/10 bg-slate-950/50 p-3">
            <h3 className="text-sm font-semibold text-white">Private conversations and team groups</h3>
            <p className="mt-1 text-xs text-slate-400">
              Chat accounts are managed separately from Employee Audit Manager accounts. Your audit login is not shared with the chat service.
            </p>
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
      ) : (
        <div className="space-y-3 rounded-xl border border-white/10 bg-slate-950/50 p-3">
          <div>
            <h3 className="text-sm font-semibold text-white">General channel</h3>
            <p className="mt-1 text-xs text-slate-400">The existing Employee Audit Manager general-channel history and send action remain available here.</p>
          </div>
          <div className="max-h-[52vh] min-h-48 space-y-2 overflow-y-auto rounded-lg bg-slate-950 p-3" role="log" aria-live="polite" aria-label="General channel messages">
            {messages.map((message, index) => (
              <div key={message.id || index} className="rounded-lg border border-white/5 bg-slate-900 p-3">
                <b className="text-xs text-cyan-300">{message.sender_name || message.username || 'User'}</b>
                <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-200">{message.content || message.message}</p>
              </div>
            ))}
            {!messages.length && <p className="py-8 text-center text-sm text-slate-500">No general-channel messages yet.</p>}
          </div>
          <form className="flex flex-col gap-2 sm:flex-row" onSubmit={sendGeneralMessage}>
            <input
              className="w-full min-w-0 rounded-lg border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400"
              placeholder="Write a general-channel message…"
              value={generalDraft}
              maxLength={4000}
              disabled={generalBusy}
              onChange={event => setGeneralDraft(event.target.value)}
            />
            <button
              type="submit"
              className="inline-flex items-center justify-center rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 disabled:opacity-50"
              disabled={generalBusy || !generalDraft.trim()}
            >
              {generalBusy ? 'Sending…' : 'Send'}
            </button>
          </form>
          {generalError && <p role="alert" className="text-xs text-rose-300">{generalError}</p>}
        </div>
      )}
    </div>
  );
}
