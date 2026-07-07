/**
 * LineProfile — 线路纵断面图
 * 基于《需求文档》UI-VW-01
 * 显示全线车站位置、区间、坡度示意
 */
import ReactECharts from 'echarts-for-react';

export default function LineProfile() {
  // TODO: 从后端获取线路配置后替换为实际数据
  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '公里标 (m)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '坡度 (‰)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '坡度',
        type: 'line',
        data: [
          [0, 5], [500, 5], [1000, 10], [1500, 10],
          [2000, 30], [2500, 30], [3200, 15],
        ],
        areaStyle: { color: 'rgba(24, 144, 255, 0.15)' },
        lineStyle: { color: '#1890ff' },
        itemStyle: { color: '#1890ff' },
        markPoint: {
          data: [
            { name: 'A站', coord: [0, 5], symbol: 'pin', symbolSize: 30 },
            { name: 'B站', coord: [1500, 10], symbol: 'pin', symbolSize: 30 },
            { name: 'C站', coord: [3200, 15], symbol: 'pin', symbolSize: 30 },
          ],
          label: { color: '#fff', fontSize: 10 },
        },
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📐 线路纵断面</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
