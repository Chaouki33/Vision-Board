import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import { formatAxis, formatExact } from "../format";
import { prefersReducedMotion } from "./AnimatedNumber";
import type { ChartData } from "../types";

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, SVGRenderer]);

/** Incrémenté à chaque changement de thème (bouton ou réglage du système). */
function useThemeVersion(): number {
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const bump = () => setVersion((v) => v + 1);
    const observer = new MutationObserver(bump);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", bump);
    return () => {
      observer.disconnect();
      media.removeEventListener("change", bump);
    };
  }, []);
  return version;
}

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function buildOption(chart: ChartData): echarts.EChartsCoreOption {
  const series = token("--chart-series");
  const muted = token("--muted");
  const text = token("--text");
  const grid = token("--chart-grid");
  const surface = token("--surface");
  const tooltip = {
    backgroundColor: surface,
    borderColor: token("--border"),
    textStyle: { color: text, fontSize: 13 },
    valueFormatter: (v: unknown) => formatExact(Number(v), chart.unit),
  };
  const axisLabel = { color: muted, fontSize: 12 };

  if (chart.type === "line") {
    const lastIndex = chart.values.length - 1;
    return {
      grid: { left: 8, right: 36, top: 28, bottom: 8, containLabel: true },
      tooltip: { ...tooltip, trigger: "axis", axisPointer: { type: "line", lineStyle: { color: muted, width: 1 } } },
      xAxis: {
        type: "category",
        data: chart.labels,
        boundaryGap: false,
        axisLabel: { ...axisLabel, hideOverlap: true },
        axisLine: { lineStyle: { color: grid } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: grid, width: 1, type: "solid" } },
        axisLabel: { ...axisLabel, formatter: (v: number) => formatAxis(v, chart.unit) },
      },
      series: [
        {
          type: "line",
          name: chart.title,
          data: chart.values.map((v, i) =>
            // Seul le dernier point porte une étiquette et un marqueur.
            i === lastIndex
              ? {
                  value: v,
                  symbol: "circle",
                  symbolSize: 9,
                  label: { show: true, position: "top", color: text, fontWeight: 600, formatter: () => formatAxis(v, chart.unit) },
                }
              : v,
          ),
          symbol: "none",
          lineStyle: { width: 2, color: series, cap: "round", join: "round" },
          itemStyle: { color: series, borderColor: surface, borderWidth: 2 },
          areaStyle: { color: series, opacity: 0.1 },
          emphasis: { focus: "none" },
        },
      ],
    };
  }

  // Barres horizontales : les libellés longs (clients, produits) restent lisibles.
  return {
    grid: { left: 8, right: 64, top: 8, bottom: 8, containLabel: true },
    tooltip: { ...tooltip, trigger: "item" },
    xAxis: {
      type: "value",
      splitNumber: 4,
      splitLine: { lineStyle: { color: grid, width: 1, type: "solid" } },
      axisLabel: { ...axisLabel, formatter: (v: number) => formatAxis(v, chart.unit) },
    },
    yAxis: {
      type: "category",
      data: chart.labels,
      inverse: true,
      axisLine: { lineStyle: { color: grid } },
      axisTick: { show: false },
      axisLabel: { ...axisLabel, color: text, width: 190, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        name: chart.title,
        data: chart.values.map((v, i) => ({
          value: v,
          itemStyle: { color: chart.labels[i] === "Autres" ? token("--chart-other") : series },
        })),
        barMaxWidth: 24,
        barCategoryGap: "30%",
        itemStyle: { borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: "right", color: muted, formatter: (p: { value: number }) => formatAxis(p.value, chart.unit) },
      },
    ],
  };
}

/** Les courbes se dessinent, les barres poussent l'une après l'autre (sauf si l'utilisateur réduit les animations). */
function withAnimation(option: echarts.EChartsCoreOption, type: ChartData["type"]): echarts.EChartsCoreOption {
  if (prefersReducedMotion()) return { ...option, animation: false };
  return {
    ...option,
    animation: true,
    animationDuration: type === "line" ? 1100 : 800,
    animationEasing: "cubicOut",
    animationDelay: type === "bar" ? (index: number) => index * 70 : 0,
    animationDurationUpdate: 400,
  };
}

export default function Chart({ chart }: { chart: ChartData }) {
  const ref = useRef<HTMLDivElement>(null);
  const themeVersion = useThemeVersion();
  const height = chart.type === "bar" ? Math.max(180, chart.labels.length * 34 + 40) : 260;

  useEffect(() => {
    if (!ref.current) return;
    const instance = echarts.init(ref.current, undefined, { renderer: "svg" });
    instance.setOption(withAnimation(buildOption(chart), chart.type));
    const resize = new ResizeObserver(() => instance.resize());
    resize.observe(ref.current);
    return () => {
      resize.disconnect();
      instance.dispose();
    };
  }, [chart, themeVersion]);

  return <div ref={ref} style={{ width: "100%", height }} role="img" aria-label={chart.title} />;
}
