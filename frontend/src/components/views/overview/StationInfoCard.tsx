/**
 * StationInfoCard — 车站信息浮动卡片
 * 点击车站时显示放大的轨道构造图 + 站务详细信息
 */
import type { StationLayout } from '../../../types/simulation';
import { formatSimTime } from '../../../utils/format';

interface StationInfoCardProps {
  station: StationLayout;
  position: { x: number; y: number };
  onClose: () => void;
}

/** 站内轨道分布大图 */
function TrackLayoutDiagram({ station }: { station: StationLayout }) {
  const W = 280;                              // SVG 宽度
  const trackSpacing = 36;                    // 股道间距
  const mainY = 30;                           // 正线 Y
  const padX = 16;                            // 左右内边距
  const trackLen = W - padX * 2;             // 股道有效长度
  const curveLen = 45;                        // 道岔曲线长度
  const sidings = station.tracks.filter(t => t.type !== 'main');
  const H = mainY + (sidings.length + 1) * trackSpacing + 16;  // SVG 高度

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
      {/* 背景 */}
      <rect x={0} y={0} width={W} height={H} fill="rgba(0,0,0,0.2)" rx={4} />

      {/* 车站封端 */}
      <line x1={padX} y1={mainY - 10} x2={padX} y2={mainY + 10} stroke="#555" strokeWidth={2} />
      <line x1={padX + trackLen} y1={mainY - 10} x2={padX + trackLen} y2={mainY + 10} stroke="#555" strokeWidth={2} />

      {/* 正线 */}
      <line
        x1={padX}
        y1={mainY}
        x2={padX + trackLen}
        y2={mainY}
        stroke="#e0e0e0"
        strokeWidth={4}
        strokeLinecap="round"
      />
      <text x={padX + 6} y={mainY - 10} fill="#ccc" fontSize={10} fontWeight={600}>正线</text>

      {/* 公里标 */}
      <text x={padX + trackLen / 2} y={H - 2} textAnchor="middle" fill="#666" fontSize={9}>
        K{(station.chainage / 1000).toFixed(2)} — {station.length}m — K{((station.chainage + station.length) / 1000).toFixed(2)}
      </text>

      {/* 侧线 + 道岔 */}
      {sidings.map((track, i) => {
        const ty = mainY + (i + 1) * trackSpacing;
        const isOccupied = track.occupied;
        const color = isOccupied ? '#ff4d4f' : (track.type === 'parking' ? '#808080' : '#a0a0a0');
        const lineStart = padX + curveLen;
        const lineEnd = padX + trackLen - curveLen;

        return (
          <g key={track.track_id}>
            {/* 占用底色 */}
            {isOccupied && (
              <rect
                x={lineStart}
                y={ty - 6}
                width={lineEnd - lineStart}
                height={12}
                fill="rgba(255, 77, 79, 0.12)"
                rx={3}
              />
            )}

            {/* 左道岔贝塞尔 */}
            <path
              d={`M ${padX},${mainY} C ${padX + curveLen * 0.4},${mainY} ${lineStart - curveLen * 0.2},${ty} ${lineStart},${ty}`}
              fill="none"
              stroke={color}
              strokeWidth={3}
              strokeLinecap="round"
            />

            {/* 侧线主体 */}
            <line
              x1={lineStart}
              y1={ty}
              x2={lineEnd}
              y2={ty}
              stroke={color}
              strokeWidth={3}
              strokeDasharray={track.type === 'parking' ? '6 3' : undefined}
              strokeLinecap="round"
            />

            {/* 右道岔贝塞尔 */}
            <path
              d={`M ${lineEnd},${ty} C ${lineEnd + curveLen * 0.2},${ty} ${padX + trackLen - curveLen * 0.4},${mainY} ${padX + trackLen},${mainY}`}
              fill="none"
              stroke={color}
              strokeWidth={3}
              strokeLinecap="round"
            />

            {/* 股道名称 + 状态 */}
            <text x={lineStart + 4} y={ty - 8} fill={isOccupied ? '#ff4d4f' : '#aaa'} fontSize={10} fontWeight={500}>
              {track.name}
            </text>
            <text x={lineEnd - 4} y={ty - 8} textAnchor="end" fill={isOccupied ? '#ff4d4f' : '#52c41a'} fontSize={9}>
              {isOccupied ? '● 占用' : '○ 空闲'}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function StationInfoCard({ station, position, onClose }: StationInfoCardProps) {
  return (
    <div
      style={{
        ...styles.card,
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* 头部 */}
      <div style={styles.header}>
        <span style={styles.title}>🏢 {station.name}</span>
        <button style={styles.closeBtn} onClick={onClose}>✕</button>
      </div>

      {/* 基本信息 */}
      <div style={styles.row}>
        <span style={styles.label}>公里标:</span>
        <span>K{(station.chainage / 1000).toFixed(3).replace('.', '+')}</span>
        <span style={{ marginLeft: 12, color: '#808080' }}>站长: {station.length}m</span>
      </div>

      {/* 轨道分布大图 */}
      <div style={styles.diagramWrap}>
        <div style={styles.sectionTitle}>轨道构造</div>
        <TrackLayoutDiagram station={station} />
      </div>

      {/* 时间信息 */}
      <div style={styles.divider} />
      <div style={styles.row}>
        <span style={styles.label}>到达:</span>
        <span>{station.arrival_time != null ? formatSimTime(station.arrival_time) : '--:--:--'}</span>
        <span style={{ marginLeft: 16, color: '#808080' }}>出发:</span>
        <span>{station.departure_time != null ? formatSimTime(station.departure_time) : '--:--:--'}</span>
      </div>
      <div style={styles.row}>
        <span style={styles.label}>停站:</span>
        <span>{station.dwell_time_actual != null ? `${station.dwell_time_actual.toFixed(0)}s` : '--'}</span>
      </div>

      {/* 站台占用 */}
      <div style={styles.divider} />
      <div style={styles.row}>
        <span style={styles.label}>站台占用:</span>
        <div style={styles.barContainer}>
          <div style={{ ...styles.barFill, width: `${station.occupancy_rate * 100}%` }} />
        </div>
        <span style={{ marginLeft: 8 }}>{(station.occupancy_rate * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    position: 'absolute',
    zIndex: 200,
    backgroundColor: 'var(--bg-dark)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    padding: '12px',
    width: '300px',
    fontSize: '12px',
    color: '#e0e0e0',
    boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
    pointerEvents: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  title: {
    fontWeight: 600,
    fontSize: '15px',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#808080',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '0 4px',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '4px',
  },
  label: {
    color: '#808080',
    marginRight: '8px',
    minWidth: '56px',
  },
  divider: {
    height: '1px',
    backgroundColor: 'var(--border-color)',
    margin: '8px 0',
  },
  sectionTitle: {
    fontSize: '11px',
    color: '#808080',
    marginBottom: '6px',
    fontWeight: 600,
    letterSpacing: '0.5px',
  },
  diagramWrap: {
    margin: '8px 0',
    padding: '8px',
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderRadius: '6px',
    border: '1px solid rgba(255,255,255,0.06)',
  },
  barContainer: {
    flex: 1,
    height: '6px',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    backgroundColor: '#1890ff',
    borderRadius: '3px',
    transition: 'width 0.3s',
  },
};
