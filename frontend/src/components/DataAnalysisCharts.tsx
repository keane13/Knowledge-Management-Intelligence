"use client";

import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis
} from "recharts";

const COLORS = ['#8b5cf6', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

interface ChartData {
  name?: string;
  value?: number;
  value1?: number;
  value2?: number;
  x?: number;
  y?: number;
  z?: number;
  [key: string]: any;
}

interface ChartConfig {
  analysisType: string;
  chartType: string;
  title: string;
  data: ChartData[];
}

export function DataAnalysisCharts({ config }: { config: ChartConfig }) {
  const { chartType, title, data } = config;

  const renderChart = () => {
    switch (chartType) {
      case "BarChart":
        if (!data || data.length === 0) return null;
        let xKeyB = "name"; let yKeyB = "value"; let yKey1B = "value1"; let yKey2B = "value2";
        if (!("name" in data[0])) xKeyB = Object.keys(data[0]).find(k => typeof data[0][k] === 'string') || Object.keys(data[0])[0];
        if (!("value" in data[0]) && !("value1" in data[0])) {
           const nums = Object.keys(data[0]).filter(k => typeof data[0][k] === 'number' && k !== xKeyB);
           if (nums.length > 0) yKeyB = nums[0];
           if (nums.length > 1) { yKey1B = nums[0]; yKey2B = nums[1]; }
        }
        
        // Check if multi-value
        const isMulti = data.length > 0 && (yKey1B in data[0] || 'value1' in data[0]);
        
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey={xKeyB} tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              {isMulti ? (
                <>
                  <Bar dataKey={yKey1B} fill={COLORS[0]} radius={[4, 4, 0, 0]} />
                  <Bar dataKey={yKey2B} fill={COLORS[1]} radius={[4, 4, 0, 0]} />
                </>
              ) : (
                <Bar dataKey={yKeyB} fill={COLORS[0]} radius={[4, 4, 0, 0]} />
              )}
            </BarChart>
          </ResponsiveContainer>
        );

      case "LineChart":
        if (!data || data.length === 0) return null;
        let xKeyL = "name"; let yKeyL = "value"; let yKey1L = "value1"; let yKey2L = "value2";
        if (!("name" in data[0])) xKeyL = Object.keys(data[0]).find(k => typeof data[0][k] === 'string') || Object.keys(data[0])[0];
        if (!("value" in data[0]) && !("value1" in data[0])) {
           const nums = Object.keys(data[0]).filter(k => typeof data[0][k] === 'number' && k !== xKeyL);
           if (nums.length > 0) yKeyL = nums[0];
           if (nums.length > 1) { yKey1L = nums[0]; yKey2L = nums[1]; }
        }
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey={xKeyL} tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Line type="monotone" dataKey={data[0]?.[yKey1L] !== undefined ? yKey1L : yKeyL} stroke={COLORS[1]} strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              {data[0]?.[yKey2L] !== undefined && (
                 <Line type="monotone" dataKey={yKey2L} stroke={COLORS[2]} strokeWidth={3} dot={{ r: 4 }} />
              )}
            </LineChart>
          </ResponsiveContainer>
        );

      case "PieChart":
        if (!data || data.length === 0) return null;
        let yKeyP = "value";
        if (!("value" in data[0])) {
           const nums = Object.keys(data[0]).filter(k => typeof data[0][k] === 'number');
           if (nums.length > 0) yKeyP = nums[0];
        }
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey={yKeyP}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
            </PieChart>
          </ResponsiveContainer>
        );

      case "ScatterChart":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" dataKey="x" name="X" tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis type="number" dataKey="y" name="Y" tick={{ fontSize: 12, fill: '#64748b' }} />
              <ZAxis type="number" range={[50, 400]} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
              <Scatter name="Correlation" data={data} fill={COLORS[2]} />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case "Heatmap":
        const xLabels = Array.from(new Set(data.map(d => d.x).filter(Boolean)));
        const yLabels = Array.from(new Set(data.map(d => d.y).filter(Boolean)));
        
        return (
          <div className="w-full overflow-x-auto py-2">
            <div className="min-w-max">
              {/* Header row */}
              <div className="flex">
                <div className="w-24 shrink-0"></div>
                {xLabels.map((x: any) => (
                  <div key={x} className="w-16 shrink-0 text-center text-xs text-slate-500 font-medium truncate px-1" title={x}>{x}</div>
                ))}
              </div>
              {/* Grid rows */}
              {yLabels.map((y: any) => (
                <div key={y} className="flex items-center mt-1">
                  <div className="w-24 shrink-0 text-xs text-slate-500 font-medium text-right pr-2 truncate" title={y}>{y}</div>
                  {xLabels.map((x: any) => {
                    const cell = data.find(d => d.x === x && d.y === y);
                    const val = cell?.value || 0;
                    const valNum = Number(val);
                    const isPositive = valNum > 0;
                    const intensity = Math.min(Math.abs(valNum), 1);
                    const bg = isPositive ? `rgba(14, 165, 233, ${intensity})` : `rgba(239, 68, 68, ${intensity})`;
                    return (
                      <div 
                        key={`${x}-${y}`} 
                        className="w-16 h-8 shrink-0 flex items-center justify-center text-[10px] font-medium border border-slate-100/50 rounded-sm transition-colors hover:brightness-95"
                        style={{ backgroundColor: bg, color: intensity > 0.4 ? 'white' : 'inherit' }}
                        title={`${x} vs ${y}: ${valNum.toFixed(2)}`}
                      >
                        {valNum.toFixed(2)}
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return <div className="text-sm text-slate-500 py-10 text-center bg-slate-50 rounded-xl border border-slate-100">Chart format not supported</div>;
    }
  };

  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200/60 shadow-sm shadow-slate-200/50 flex flex-col hover:border-sky-200 transition-colors">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="font-bold text-slate-800 text-sm">{title}</h3>
          <p className="text-[10px] uppercase font-bold text-slate-400 mt-1 tracking-wider">{config.analysisType} ANALYSIS</p>
        </div>
      </div>
      <div className="flex-1 w-full">
        {renderChart()}
      </div>
    </div>
  );
}
