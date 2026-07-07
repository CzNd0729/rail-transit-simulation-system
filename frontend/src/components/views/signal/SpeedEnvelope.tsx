/**
 * SpeedEnvelope — 速度包络线图
 * 基于《需求文档》UI-SIG-02（迭代三）
 * ATP 紧急制动触发曲线 vs 实际运行曲线
 */
export default function SpeedEnvelope() {
  // TODO: 迭代三实现 — ECharts 绘制速度包络线
  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📉 速度包络线</div>
      <div style={styles.placeholder}>
        <span>速度包络线将在迭代三实现</span>
        <span style={styles.hint}>ATP 紧急制动触发曲线 vs 实际运行曲线</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  placeholder: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: 'calc(100% - 30px)',
    color: 'var(--text-secondary)',
    fontSize: '13px',
    gap: '8px',
  },
  hint: {
    fontSize: '11px',
    opacity: 0.7,
  },
};
