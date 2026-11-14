// Thin Recharts wrappers with consistent styling.
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { SEVERITY_COLORS } from "../../utils/formatters";

const SEVS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

export function AlarmsPerDayChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} fontSize={11} />
        <YAxis fontSize={11} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {SEVS.slice().reverse().map((s) => (
          <Bar key={s} dataKey={s} stackId="a" fill={SEVERITY_COLORS[s]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function SimpleBarChart({ data, x, y, color = "#94a3b8", height = 240, horizontal = false }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"}
                margin={{ top: 5, right: 10, left: horizontal ? 40 : -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={horizontal} horizontal={!horizontal} />
        {horizontal ? (
          <>
            <XAxis type="number" fontSize={11} />
            <YAxis type="category" dataKey={x} fontSize={11} width={110} />
          </>
        ) : (
          <>
            <XAxis dataKey={x} fontSize={11} />
            <YAxis fontSize={11} />
          </>
        )}
        <Tooltip />
        <Bar dataKey={y} fill={color} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TrendLine({ data, x, lines, height = 240 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={x} fontSize={11} />
        <YAxis fontSize={11} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {lines.map(([key, color]) => (
          <Line key={key} type="monotone" dataKey={key} stroke={color} dot={false} strokeWidth={2} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}