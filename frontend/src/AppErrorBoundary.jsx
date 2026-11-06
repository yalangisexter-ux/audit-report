import React from 'react';

export default class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('Raw Strength workspace render failure:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main
          role="alert"
          aria-labelledby="rsc-render-error-title"
          className="fixed inset-0 z-[9999] flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8 text-slate-100"
        >
          <section className="w-full max-w-lg rounded-3xl border border-cyan-300/20 bg-slate-900/95 p-7 text-center shadow-2xl shadow-black/40">
            <div className="mb-4 text-sm font-black tracking-[0.24em] text-cyan-300">
              RAW STRENGTH CALISTHENICS
            </div>
            <h1 id="rsc-render-error-title" className="text-2xl font-black">
              Workspace could not be loaded
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              The application encountered a display error. Reload the page to restore your workspace.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-6 inline-flex min-h-11 items-center justify-center rounded-xl bg-cyan-400 px-5 py-3 text-sm font-bold text-slate-950 hover:bg-cyan-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-200"
            >
              Reload workspace
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
