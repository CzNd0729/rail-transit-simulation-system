/**
 * EnergyChart — 能耗累计图
 * 基于《需求文档》UI-VHC-05（迭代三）
 * 牵引能耗/再生制动电量的累计柱状图
 */
export default function EnergyChart() {
  // TODO: 迭代三实现
  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🔋 能耗累计</div>
      <div style={styles.placeholder}>
        <span>能耗累计图将在迭代三实现</span>
        <span style={styles.hint}>牵引能耗 / 再生制动电量 累计统计</span>
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
