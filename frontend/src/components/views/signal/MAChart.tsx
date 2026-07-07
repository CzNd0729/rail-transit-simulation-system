/**
 * MAChart — 移动授权（MA）示意图
 * 基于《需求文档》UI-SIG-01（迭代三）
 * 显示各列车安全包络和追踪间隔
 */
export default function MAChart() {
  // TODO: 迭代三实现 — ECharts 绘制各列车 MA 安全包络
  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🛡️ 移动授权 (MA)</div>
      <div style={styles.placeholder}>
        <span>移动授权示意图将在迭代三实现</span>
        <span style={styles.hint}>ATP 安全包络 + 追踪间隔可视化</span>
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
    color: 'var(--text-secondary)',
    opacity: 0.7,
  },
};
