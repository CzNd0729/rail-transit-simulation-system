/**
 * TimetableChart — 运行图（时间-距离图）
 * 基于《需求文档》UI-SIG-03（迭代三）
 * 多列车时空轨迹绘制
 */
export default function TimetableChart() {
  // TODO: 迭代三实现 — ECharts 绘制运行图
  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📅 运行图</div>
      <div style={styles.placeholder}>
        <span>运行图将在迭代三实现</span>
        <span style={styles.hint}>多列车时空轨迹（时间-距离图）</span>
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
