/**
 * LineProfileDetail — 线路剖面图（详细版）
 * 基于《需求文档》UI-TRK-01（迭代三）
 * 坡度-距离剖面，标注车站和区间
 */
export default function LineProfileDetail() {
  // TODO: 迭代三实现 — 详细的坡度-距离剖面图
  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🏔️ 线路剖面图</div>
      <div style={styles.placeholder}>
        <span>线路剖面图将在迭代三实现</span>
        <span style={styles.hint}>坡度-距离剖面 + 车站标注 + 区间着色</span>
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
