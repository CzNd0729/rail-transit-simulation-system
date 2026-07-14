import { useEffect, useLayoutEffect, useRef, type CSSProperties } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { useChartActive } from './ChartLifecycleContext';
import { useChartSwitchGate } from './ChartSwitchGate';

export interface SimEChartProps {
  option: EChartsOption;
  style?: CSSProperties;
  className?: string;
}

const IDLE_THROTTLE_MS = 150;

/** 拷贝 series.data，避免 chartHistory 原地 mutate 与 ECharts 共享引用 */
function cloneOptionForPaint(option: EChartsOption): EChartsOption {
  const series = option.series;
  if (!Array.isArray(series)) return option;
  return {
    ...option,
    series: series.map((s) => {
      if (!s || typeof s !== 'object') return s;
      const data = (s as { data?: unknown }).data;
      if (!Array.isArray(data)) return s;
      return { ...s, data: data.slice() };
    }),
  };
}

/**
 * 命令式 ECharts：双层 host + 延迟 dispose，降低 React 19 removeChild 冲突。
 * ChartSwitchGate.switching 期间禁止绘制；idle 节流；settling 立即补帧。
 */
export default function SimEChart({ option, style, className }: SimEChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const chartElRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const optionRef = useRef(option);
  const lastPaintAtRef = useRef(0);
  const viewActive = useChartActive();
  const { phase, canPaint } = useChartSwitchGate();

  optionRef.current = option;

  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const chartEl = document.createElement('div');
    chartEl.style.width = '100%';
    chartEl.style.height = '100%';
    host.appendChild(chartEl);
    chartElRef.current = chartEl;

    const chart = echarts.init(chartEl);
    chartRef.current = chart;
    chart.setOption(cloneOptionForPaint(optionRef.current));

    const resizeObserver = new ResizeObserver(() => {
      if (!canPaint || !viewActive) return;
      chart.resize();
    });
    resizeObserver.observe(chartEl);

    return () => {
      resizeObserver.disconnect();
      const instance = chartRef.current;
      chartRef.current = null;
      chartElRef.current = null;
      window.setTimeout(() => {
        try {
          instance?.dispose();
        } catch {
          /* ignore */
        }
        if (chartEl.parentNode === host) {
          try {
            host.removeChild(chartEl);
          } catch {
            /* ignore */
          }
        }
      }, 0);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !viewActive || !canPaint) return;

    const now = performance.now();
    const immediate = phase === 'settling';
    if (!immediate && now - lastPaintAtRef.current < IDLE_THROTTLE_MS) {
      const delay = IDLE_THROTTLE_MS - (now - lastPaintAtRef.current);
      const timer = window.setTimeout(() => {
        if (!chartRef.current || !viewActive) return;
        lastPaintAtRef.current = performance.now();
        chartRef.current.setOption(cloneOptionForPaint(optionRef.current), {
          lazyUpdate: true,
          replaceMerge: ['series', 'legend'],
        });
      }, delay);
      return () => window.clearTimeout(timer);
    }

    lastPaintAtRef.current = now;
    let frameId = 0;
    frameId = requestAnimationFrame(() => {
      chart.setOption(cloneOptionForPaint(optionRef.current), {
        lazyUpdate: true,
        replaceMerge: ['series', 'legend'],
      });
    });
    return () => cancelAnimationFrame(frameId);
  }, [option, viewActive, canPaint, phase]);

  return (
    <div
      ref={hostRef}
      className={className}
      style={{ width: '100%', height: '100%', ...style }}
    />
  );
}
