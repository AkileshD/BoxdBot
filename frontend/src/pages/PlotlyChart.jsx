import { useMemo } from 'react';
import Plot from 'react-plotly.js';

export default function PlotlyChart({ chartJson }) {
  const { data, layout } = useMemo(() => {
    try {
      return JSON.parse(chartJson);
    } catch {
      return { data: [], layout: {} };
    }
  }, [chartJson]);

  // Strip any gradient fills — strict flat style to match our palette
  const flatLayout = {
    ...layout,
    paper_bgcolor: '#F4F4F0',
    plot_bgcolor: '#F4F4F0',
    font: { family: 'IBM Plex Mono, monospace', color: '#1A1A1A', size: 11 },
    margin: { l: 48, r: 20, t: 24, b: 48 },
  };

  return (
    <Plot
      data={data}
      layout={flatLayout}
      style={{ width: '100%', height: 300 }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
