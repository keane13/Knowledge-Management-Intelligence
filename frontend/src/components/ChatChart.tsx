import { BarChart, Bar, LineChart, Line, XAxis, YAxis,
         CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export function ChatChart({ chartType, chartData }: { chartType: string; chartData: any[] }) {
  if (!chartData?.length || chartType === "NO_CHART_NEEDED") return null;

  const parsed = chartData.map(row => {
    const r: any = { ...row };
    for (const k in r)
      if (typeof r[k] === "string" && !isNaN(Number(r[k]))) r[k] = Number(r[k]);
    return r;
  });

  let xKey = Object.keys(parsed[0])[0];
  let yKey = Object.keys(parsed[0])[1];
  for (const k in parsed[0]) if (typeof parsed[0][k] === "string") xKey = k;
  for (const k in parsed[0]) if (typeof parsed[0][k] === "number") { yKey = k; break; }

  const props = { data: parsed, margin: { top: 5, right: 20, left: 0, bottom: 5 } };
  const tip = { backgroundColor: "#1e293b", borderColor: "#334155",
                borderRadius: "8px", fontSize: "12px" };

  return (
    <div className="mt-4 h-64 w-full rounded-xl border border-gray-700 p-4 bg-gray-900/50">
      <ResponsiveContainer width="100%" height="100%">
        {chartType === "Bar Chart" ? (
          <BarChart {...props}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
            <XAxis dataKey={xKey} stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
            <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: "#ffffff08" }} contentStyle={tip} />
            <Bar dataKey={yKey} fill="#06b6d4" radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        ) : (
          <LineChart {...props}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
            <XAxis dataKey={xKey} stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
            <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={tip} />
            <Line type="monotone" dataKey={yKey} stroke="#a855f7" strokeWidth={3}
              dot={{ fill: "#a855f7", strokeWidth: 2 }} activeDot={{ r: 6 }} />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
