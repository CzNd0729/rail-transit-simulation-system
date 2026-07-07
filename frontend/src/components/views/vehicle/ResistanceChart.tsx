/**
 * ResistanceChart — 阻力分解图
 * 基于《需求文档》UI-VHC-04（迭代三）
 * 堆叠面积图或柱状图，展示各阻力分量占比
 */
export default function ResistanceChart() {
  // TODO: 迭代三实现
  // 展示 Davis 基本阻力、坡度附加阻力、弯道附加阻力、隧道空气阻力的分解
  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📊 阻力分解</div>
      <div style={styles.placeholder}>
        <span>阻力分解图将在迭代三实现</span>
        <span style={styles.hint}>Davis阻力 / 坡度阻力 / 弯道阻力 / 隧道阻力</span>
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
