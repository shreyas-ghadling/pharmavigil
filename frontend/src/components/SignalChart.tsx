import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Signal } from "../types";
export default function SignalChart({ signals }: { signals: Signal[] }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={signals.map((s) => ({
            ...s,
            name: `${s.medicine} (${s.medicine_id ?? "legacy"}): ${s.symptom}`,
          }))}
          layout="vertical"
          margin={{ left: 10, right: 25 }}
        >
          <CartesianGrid stroke="#eef0f4" horizontal={false} />
          <XAxis type="number" tickLine={false} axisLine={false} />
          <YAxis
            type="category"
            dataKey="name"
            width={170}
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip />
          <Bar
            dataKey="priority_score"
            name="Review priority score"
            fill="#465fff"
            radius={[0, 5, 5, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
