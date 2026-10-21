import React, { useState } from 'react';
import { Bell, ArrowUpRight, TrendingUp, Sliders, ShieldAlert, Cpu } from 'lucide-react';

export default function AuroraCommandHUD({ onNavigate }) {
  const [scenario, setScenario] = useState('Aggressive Growth [ACTIVE]');
  const [sliders, setSliders] = useState([
    { dept: 'Engineering', hc: 230, burn: '$488', eff: '4.87%', toggle: true, val: 50 },
    { dept: 'Marketing', hc: 100, burn: '$160k', eff: '2.89%', toggle: true, val: 20 },
    { dept: 'Sales', hc: 130, burn: '$488', eff: '2.35%', toggle: true, val: 25 },
    { dept: 'Operations', hc: 100, burn: '$350k', eff: '2.89%', toggle: true, val: 90 },
    { dept: 'Engineering Core', hc: 100, burn: '$458', eff: '3.99%', toggle: true, val: 20 },
    { dept: 'Managing', hc: 90, burn: '$100k', eff: '4.39%', toggle: true, val: 30 },
    { dept: 'Operations Desk', hc: 70, burn: '$488', eff: '1.39%', toggle: true, val: 15 },
  ]);

  const handleSliderChange = (idx, newVal) => {
    setSliders(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], val: parseInt(newVal, 10) };
      return copy;
    });
  };

  const handleToggle = (idx) => {
    setSliders(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], toggle: !copy[idx].toggle };
      return copy;
    });
  };

  return (
    <div className="space-y-5">
      {/* 1. TOP STRIP: KPI Sparklines + Scenario Switcher + Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Global Liquidity */}
        <div className="p-4 rounded-2xl bg-gradient-to-b from-[#0D1424] to-[#080C14] border border-cyan-400/25 flex items-center justify-between shadow-lg shadow-cyan-950/20">
          <div>
            <div className="text-[10px] font-bold text-slate-400 tracking-wider uppercase">GLOBAL LIQUIDITY:</div>
            <div className="text-2xl font-black text-white mt-1">$428.4M</div>
          </div>
          <svg className="w-28 h-11 overflow-visible" viewBox="0 0 100 35">
            <defs>
              <linearGradient id="cyanSparkGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#00F0FF" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path d="M 0 25 C 20 18, 40 30, 60 12 C 75 22, 90 5, 100 2 L 100 35 L 0 35 Z" fill="url(#cyanSparkGrad)" />
            <path d="M 0 25 C 20 18, 40 30, 60 12 C 75 22, 90 5, 100 2" fill="none" stroke="#00F0FF" strokeWidth="2.2" strokeLinecap="round" />
            <circle cx="100" cy="2" r="3.5" fill="#FFFFFF" stroke="#00F0FF" strokeWidth="2" />
          </svg>
        </div>

        {/* Metric 2: Enterprise Valuation */}
        <div className="p-4 rounded-2xl bg-gradient-to-b from-[#0D1424] to-[#080C14] border border-emerald-400/25 flex items-center justify-between shadow-lg shadow-emerald-950/20">
          <div>
            <div className="text-[10px] font-bold text-slate-400 tracking-wider uppercase">ENTERPRISE VALUATION:</div>
            <div className="text-2xl font-black text-white mt-1">$2.14B</div>
          </div>
          <svg className="w-28 h-11 overflow-visible" viewBox="0 0 100 35">
            <defs>
              <linearGradient id="emeraldSparkGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10B981" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path d="M 0 28 C 25 24, 45 32, 65 14 C 80 18, 90 8, 100 3 L 100 35 L 0 35 Z" fill="url(#emeraldSparkGrad)" />
            <path d="M 0 28 C 25 24, 45 32, 65 14 C 80 18, 90 8, 100 3" fill="none" stroke="#10B981" strokeWidth="2.2" strokeLinecap="round" />
            <circle cx="100" cy="3" r="3.5" fill="#FFFFFF" stroke="#10B981" strokeWidth="2" />
          </svg>
        </div>

        {/* Scenario Switcher */}
        <div className="p-4 rounded-2xl bg-gradient-to-b from-[#0D1424] to-[#080C14] border border-cyan-400/25 flex flex-col justify-center">
          <div className="text-[10px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">SCENARIO SWITCH:</div>
          <select 
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="bg-[#090E1A] text-cyan-400 border border-cyan-400/80 rounded-xl px-3 py-1.5 text-xs font-bold focus:outline-none focus:ring-1 focus:ring-cyan-400"
          >
            <option>Aggressive Growth [ACTIVE]</option>
            <option>Base Case Baseline</option>
            <option>Recession Stress Test</option>
            <option>Peak Season Scaled</option>
          </select>
        </div>

        {/* Quick Intelligence & Notification */}
        <div className="p-4 rounded-2xl bg-gradient-to-b from-[#0D1424] to-[#080C14] border border-cyan-400/25 flex flex-col justify-between">
          <button 
            onClick={() => onNavigate && onNavigate('chat')}
            className="flex items-center justify-between px-3 py-2 rounded-xl bg-rose-500/10 text-rose-300 border border-rose-500/30 text-xs font-bold hover:bg-rose-500/20 transition-all"
          >
            <span className="flex items-center gap-2">
              <Bell className="w-3.5 h-3.5 text-rose-400" /> Interactive Notification
            </span>
            <span className="w-2 h-2 rounded-full bg-rose-400 animate-ping"></span>
          </button>
          <div className="flex items-center justify-between mt-2 text-[10px] text-cyan-300 bg-cyan-950/40 border border-cyan-400/20 px-2.5 py-1 rounded-lg font-bold">
            <span>Short-term Trends</span>
            <span className="bg-cyan-500/20 text-cyan-300 px-1.5 py-0.5 rounded text-[9px]">KPI ACTIVE</span>
          </div>
        </div>
      </div>

      {/* 2. CENTERPIECE: Visual Enterprise Capital Diagram */}
      <div className="p-5 rounded-2xl bg-gradient-to-b from-[#090E1A] to-[#060912] border border-cyan-400/30 relative overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#00F0FF]"></span>
            <h3 className="text-sm font-bold text-white tracking-wide">Enterprise Capital Diagram</h3>
          </div>
          <div className="text-[11px] font-bold text-slate-400 flex items-center gap-2">
            <span>ROUTING: <span className="text-emerald-400">OPTIMIZED</span></span>
            <span>•</span>
            <span>FLOW: <span className="text-cyan-400">ACTIVE</span></span>
          </div>
        </div>

        {/* SVG Bezier Flow Graph */}
        <div className="relative w-full h-72">
          <svg className="w-full h-full" viewBox="0 0 900 280" preserveAspectRatio="none">
            <defs>
              <linearGradient id="cyanRibbon" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#A855F7" stopOpacity="0.4" />
              </linearGradient>
              <linearGradient id="emeraldRibbon" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.5" />
                <stop offset="100%" stopColor="#10B981" stopOpacity="0.5" />
              </linearGradient>
              <linearGradient id="blueRibbon" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.5" />
                <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.5" />
              </linearGradient>
              <linearGradient id="indigoRibbon" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.5" />
                <stop offset="100%" stopColor="#818CF8" stopOpacity="0.5" />
              </linearGradient>
            </defs>

            {/* Bezier Bands Layer 1 -> Layer 2 */}
            <path d="M 140 135 C 240 135, 260 40, 360 40 L 360 60 C 260 60, 240 145, 140 145 Z" fill="url(#cyanRibbon)" />
            <path d="M 140 140 C 240 140, 260 105, 360 105 L 360 125 C 260 125, 240 150, 140 150 Z" fill="url(#emeraldRibbon)" />
            <path d="M 140 145 C 240 145, 260 175, 360 175 L 360 195 C 260 195, 240 155, 140 155 Z" fill="url(#blueRibbon)" />
            <path d="M 140 150 C 240 150, 260 235, 360 235 L 360 255 C 260 255, 240 160, 140 160 Z" fill="url(#indigoRibbon)" />

            {/* Bezier Bands Layer 2 -> Layer 3 */}
            <path d="M 540 50 C 640 50, 660 60, 760 60 L 760 80 C 660 80, 640 70, 540 70 Z" fill="url(#cyanRibbon)" />
            <path d="M 540 115 C 640 115, 660 140, 760 140 L 760 160 C 660 160, 640 135, 540 135 Z" fill="url(#emeraldRibbon)" />
            <path d="M 540 185 C 640 185, 660 150, 760 150 L 760 170 C 660 170, 640 205, 540 205 Z" fill="url(#blueRibbon)" />
            <path d="M 540 245 C 640 245, 660 220, 760 220 L 760 240 C 660 240, 640 265, 540 265 Z" fill="url(#indigoRibbon)" />
          </svg>

          {/* Node 1: Left Source */}
          <div className="absolute left-2 top-[108px] w-36 p-3 rounded-xl bg-[#0D1322]/90 border border-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.25)] flex flex-col justify-center">
            <span className="text-[11px] font-bold text-white">Revenue Streams</span>
            <span className="text-sm font-black text-cyan-400">$428.4M</span>
          </div>

          {/* Nodes Layer 2 (Middle) */}
          <div className="absolute left-[360px] top-[22px] w-48 p-2.5 rounded-xl bg-[#0D1322]/90 border border-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.2)]">
            <div className="text-[11px] font-bold text-white flex items-center justify-between">
              <span>Automated Payroll</span>
              <span className="w-2 h-2 rounded-full bg-purple-400"></span>
            </div>
            <span className="text-xs font-black text-purple-400">$3900k</span>
          </div>

          <div className="absolute left-[360px] top-[90px] w-48 p-2.5 rounded-xl bg-[#0D1322]/90 border border-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
            <div className="text-[11px] font-bold text-white flex items-center justify-between">
              <span>R&D Core</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            </div>
            <div className="text-[9px] text-slate-400 truncate">Transaction/sec data</div>
            <span className="text-xs font-black text-emerald-400">$428.4M - $2280k</span>
          </div>

          <div className="absolute left-[360px] top-[162px] w-48 p-2.5 rounded-xl bg-[#0D1322]/90 border border-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
            <div className="text-[11px] font-bold text-white flex items-center justify-between">
              <span>Cloud infrastructure</span>
              <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            </div>
            <span className="text-xs font-black text-cyan-400">$300k - $180k</span>
          </div>

          <div className="absolute left-[360px] top-[222px] w-48 p-2.5 rounded-xl bg-[#0D1322]/90 border border-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.2)]">
            <div className="text-[11px] font-bold text-white flex items-center justify-between">
              <span>Yield infrastructure</span>
              <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
            </div>
            <span className="text-xs font-black text-indigo-400">$200k - $1200k</span>
          </div>

          {/* Nodes Layer 3 (Right Destinations) */}
          <div className="absolute right-4 top-[45px] w-36 p-2.5 rounded-xl bg-[#0D1322]/90 border border-purple-400">
            <span className="text-[11px] font-bold text-white block">Revenue Streams</span>
            <span className="text-xs font-black text-purple-400">$428.4M</span>
          </div>

          <div className="absolute right-4 top-[125px] w-36 p-2.5 rounded-xl bg-[#0D1322]/90 border border-emerald-400">
            <span className="text-[11px] font-bold text-white block">R&D Core</span>
            <span className="text-xs font-black text-emerald-400">$2394k</span>
          </div>

          <div className="absolute right-4 top-[205px] w-36 p-2.5 rounded-xl bg-[#0D1322]/90 border border-purple-300">
            <span className="text-[11px] font-bold text-white block">Yield Returns</span>
            <span className="text-xs font-black text-purple-300">$1350k</span>
          </div>
        </div>
      </div>

      {/* 3. BOTTOM ROW: Matrix Grid + Intelligence Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Matrix Grid Table (7 cols) */}
        <div className="lg:col-span-7 p-5 rounded-2xl bg-gradient-to-b from-[#0D1322] to-[#080C14] border border-cyan-400/25">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-white tracking-wide">Matrix Grid</h3>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Frequency updated:</span>
              <select className="bg-[#090E1A] text-cyan-400 border border-cyan-400/50 rounded-lg px-2 py-0.5 text-[11px] font-bold">
                <option>Department date</option>
                <option>Daily EOD sync</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-cyan-400/30 text-[10px] uppercase font-bold text-slate-400">
                  <th className="py-2.5 pr-2">Department</th>
                  <th className="py-2.5 px-2 text-center">Headcounts</th>
                  <th className="py-2.5 px-2 text-center">Burn Rate</th>
                  <th className="py-2.5 px-2 text-center">Efficiency</th>
                  <th className="py-2.5 px-2 text-center">Toggle</th>
                  <th className="py-2.5 pl-2 text-right">Real-Time Budget</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {sliders.map((row, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02]">
                    <td className="py-2.5 pr-2 font-bold text-white whitespace-nowrap">{row.dept}</td>
                    <td className="py-2.5 px-2 text-center text-slate-300 font-semibold">{row.hc}</td>
                    <td className="py-2.5 px-2 text-center text-slate-300 font-semibold">{row.burn}</td>
                    <td className="py-2.5 px-2 text-center text-cyan-400 font-bold">{row.eff}</td>
                    <td className="py-2.5 px-2 text-center">
                      <button
                        onClick={() => handleToggle(idx)}
                        className={`px-2 py-0.5 rounded-full text-[9px] font-black tracking-wider transition-all border ${
                          row.toggle
                            ? 'bg-cyan-500/20 text-cyan-400 border-cyan-400 shadow-[0_0_8px_rgba(0,240,255,0.4)]'
                            : 'bg-slate-800 text-slate-500 border-slate-700'
                        }`}
                      >
                        {row.toggle ? '● ON' : '○ OFF'}
                      </button>
                    </td>
                    <td className="py-2.5 pl-2 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={row.val}
                          onChange={(e) => handleSliderChange(idx, e.target.value)}
                          className="w-24 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                        />
                        <span className="w-8 text-[11px] font-mono font-bold text-cyan-400">{row.val}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Intelligence Panel (Radar + Heatmap + Action Pills) (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Radar / Spider Chart */}
          <div className="p-4 rounded-2xl bg-gradient-to-b from-[#0D1322] to-[#080C14] border border-cyan-400/25">
            <h4 className="text-xs font-bold text-white mb-2">Anomaly & Predictive Risk Engine</h4>
            <div className="flex items-center justify-center">
              <svg className="w-52 h-44 overflow-visible" viewBox="-100 -100 200 200">
                {/* 4 Concentric Hexagons */}
                {[25, 50, 75, 100].map(r => (
                  <polygon
                    key={r}
                    points="0,-100 86.6,-50 86.6,50 0,100 -86.6,50 -86.6,-50"
                    transform={`scale(${r / 100})`}
                    fill="none"
                    stroke="rgba(255,255,255,0.12)"
                    strokeDasharray="2,2"
                  />
                ))}
                {/* 6 Axis Lines */}
                <line x1="0" y1="0" x2="0" y2="-100" stroke="rgba(255,255,255,0.15)" />
                <line x1="0" y1="0" x2="86.6" y2="-50" stroke="rgba(255,255,255,0.15)" />
                <line x1="0" y1="0" x2="86.6" y2="50" stroke="rgba(255,255,255,0.15)" />
                <line x1="0" y1="0" x2="0" y2="100" stroke="rgba(255,255,255,0.15)" />
                <line x1="0" y1="0" x2="-86.6" y2="50" stroke="rgba(255,255,255,0.15)" />
                <line x1="0" y1="0" x2="-86.6" y2="-50" stroke="rgba(255,255,255,0.15)" />

                {/* Data Polygon */}
                <polygon
                  points="0,-72 38.9,-22.5 73.6,42.5 0,40 -47.6,27.5 -56.3,-32.5"
                  fill="rgba(0,240,255,0.25)"
                  stroke="#00F0FF"
                  strokeWidth="2"
                />

                {/* Vertices */}
                <circle cx="0" cy="-72" r="3" fill="#FFFFFF" stroke="#00F0FF" strokeWidth="1.5" />
                <circle cx="38.9" cy="-22.5" r="3" fill="#FFFFFF" stroke="#00F0FF" strokeWidth="1.5" />
                <circle cx="73.6" cy="42.5" r="3" fill="#FFFFFF" stroke="#00F0FF" strokeWidth="1.5" />
                <circle cx="0" cy="40" r="3" fill="#FFFFFF" stroke="#00F0FF" strokeWidth="1.5" />
                <circle cx="-47.6" cy="27.5" r="3" fill="#FFFFFF" stroke="#00F0FF" strokeWidth="1.5" />
                <circle cx="-56.3" cy="-32.5" r="3" fill="#FFFFFF" stroke="#00F0FF" strokeWidth="1.5" />

                {/* Labels */}
                <text x="0" y="-108" textAnchor="middle" fill="#94A3B8" fontSize="8" fontWeight="bold">Market</text>
                <text x="96" y="-50" textAnchor="start" fill="#94A3B8" fontSize="8" fontWeight="bold">Ops</text>
                <text x="96" y="55" textAnchor="start" fill="#94A3B8" fontSize="8" fontWeight="bold">Talent</text>
                <text x="0" y="116" textAnchor="middle" fill="#94A3B8" fontSize="8" fontWeight="bold">Retention</text>
                <text x="-96" y="55" textAnchor="end" fill="#94A3B8" fontSize="8" fontWeight="bold">Capacity</text>
                <text x="-96" y="-50" textAnchor="end" fill="#94A3B8" fontSize="8" fontWeight="bold">Runway</text>
              </svg>
            </div>
          </div>

          {/* Talent Attrition Risk Heatmap */}
          <div className="p-4 rounded-2xl bg-gradient-to-b from-[#0D1322] to-[#080C14] border border-cyan-400/25">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-white">Talent Attrition Risk Heatmap</h4>
              <span className="text-[10px] font-bold text-rose-400">■ Risk ■ Amber ■ Safe</span>
            </div>
            <div className="grid grid-cols-9 gap-1.5 text-center text-[10px]">
              <div></div>
              {['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8'].map(t => (
                <div key={t} className="text-slate-500 font-bold">{t}</div>
              ))}

              <div className="text-slate-400 font-bold text-left">Team</div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>

              <div className="text-slate-400 font-bold text-left">Team</div>
              <div className="h-4 rounded bg-emerald-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>

              <div className="text-slate-400 font-bold text-left">Sales</div>
              <div className="h-4 rounded bg-emerald-500"></div>
              <div className="h-4 rounded bg-emerald-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-rose-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>

              <div className="text-slate-400 font-bold text-left">Ops</div>
              <div className="h-4 rounded bg-emerald-500"></div>
              <div className="h-4 rounded bg-emerald-500"></div>
              <div className="h-4 rounded bg-emerald-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
              <div className="h-4 rounded bg-amber-500"></div>
            </div>
          </div>

          {/* AI-Powered Action Pills */}
          <div className="p-4 rounded-2xl bg-gradient-to-b from-[#0D1322] to-[#080C14] border border-cyan-400/25 space-y-2">
            <h4 className="text-xs font-bold text-white">AI-powered Recommendation Action pills</h4>
            <div className="flex flex-col gap-1.5">
              <button 
                onClick={() => onNavigate && onNavigate('business')}
                className="w-full text-left px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 text-xs font-bold tracking-wide transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)]"
              >
                [Rebalance Q3 Cloud Reserve +$240k]
              </button>
              <button 
                onClick={() => onNavigate && onNavigate('employees')}
                className="w-full text-left px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 text-xs font-bold tracking-wide transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)]"
              >
                [Accelerate R&D Hiring: 12 FTEs]
              </button>
              <button 
                onClick={() => onNavigate && onNavigate('attendance')}
                className="w-full text-left px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 text-xs font-bold tracking-wide transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)]"
              >
                [Audit Athlete Compliance: 100% Verified]
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
