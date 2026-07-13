import { useEffect, useRef, type CSSProperties } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';

export interface SimEChartProps {
  option: EChartsOption;
  style?: CSSProperties;
  className?: string;
}

/**
 * 命令式 ECharts 容器。
 * echarts-for-react 在 React 19 高频 setState 下会与 DOM reconcile 冲突（insertBefore）。
 * 本组件只保留一个空 div 给 React 管理，图表更新走 setOption。
 */
export default function SimEChart({ option, style, className }: SimEChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const optionRef = useRef(option);
  optionRef.current = option;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = echarts.init(el);
    chartRef.current = chart;
    chart.setOption(optionRef.current);

    const resizeObserver = new ResizeObserver(() => {
      chart.resize();
    });
    resizeObserver.observe(el);

    return () => {
      resizeObserver.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    let frameId = 0;
    frameId = requestAnimationFrame(() => {
      chart.setOption(optionRef.current, {
        lazyUpdate: true,
        replaceMerge: ['series', 'legend'],
      });
    });

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [option]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', height: '100%', ...style }}
    />
  );
}
