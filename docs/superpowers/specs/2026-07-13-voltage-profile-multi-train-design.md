# VoltageProfile 多车独立图表设计

## 背景

当前 VoltageProfile 使用多车叠加曲线，但在实际运行中曲线错乱。改为每列车一张独立网压分布图，纵向堆叠、可滚动。

## 设计

- **布局**：VoltageProfile 内部按 `trains` 生成子图数组，每车一个独立 ReactECharts 实例
- **排序**：按 `selectedTrainId` 排序——选中车置顶
- **数据**：每个子图从 `chartHistory.byTrain[id].voltagePosition` 独立读取，互不干扰
- **变电所**：每张子图均显示变电所标记
- **切换器**：复用 TopBar 已有 TrainSelector + `selectedTrainId`
- **滚动**：容器 `overflow-y: auto`

## 涉及文件

- `frontend/src/components/views/power/VoltageProfile.tsx` — 重写为多子图布局
- `frontend/src/pages/PowerView.tsx` — 调整布局分配（图表区可滚动 vs 变电所面板）
