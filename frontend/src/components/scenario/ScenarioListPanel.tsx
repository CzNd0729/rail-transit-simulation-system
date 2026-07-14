/**
 * ScenarioListPanel — 方案列表+勾选面板
 * 展示所有已保存方案，支持勾选、加载、删除
 */
import { useSimulationState } from '../../context/SimulationContext';
import { deleteScenario, applyScenario, renameScenario } from '../../services/api';
import type { ScenarioSummary } from '../../types/simulation';
import { formatSimTime } from '../../utils/format';
import { useState, useRef, useEffect } from 'react';

interface ScenarioListPanelProps {
  scenarios: ScenarioSummary[];
  checkedIds: Set<string>;
  onToggle: (id: string) => void;
  onDeleted: () => void;
  onApplied: () => void;
  loading: boolean;
}

export default function ScenarioListPanel({
  scenarios,
  checkedIds,
  onToggle,
  onDeleted,
  onApplied,
  loading,
}: ScenarioListPanelProps) {
  const { runState } = useSimulationState();
  const isRunning = runState === 'running';
  const [renaming, setRenaming] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renaming) {
      const s = scenarios.find((x) => x.id === renaming);
      setEditValue(s?.name ?? '');
      // 延迟让 DOM 渲染后再 focus
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [renaming, scenarios]);

  const handleStartRename = (id: string) => {
    setRenaming(id);
  };

  const handleSubmitRename = async () => {
    const id = renaming;
    if (!id) return;
    const name = editValue.trim();
    if (!name) {
      setRenaming(null);
      return;
    }
    try {
      await renameScenario(id, name);
      onDeleted(); // 复用刷新列表
    } catch {
      alert('重命名失败');
    }
    setRenaming(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmitRename();
    } else if (e.key === 'Escape') {
      setRenaming(null);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确认删除方案「${name}」？此操作不可撤销。`)) return;
    try {
      await deleteScenario(id);
      onDeleted();
    } catch {
      alert('删除失败');
    }
  };

  const handleApply = async (id: string) => {
    if (isRunning) {
      alert('请先暂停或停止仿真');
      return;
    }
    try {
      await applyScenario(id);
      onApplied();
    } catch {
      alert('加载方案失败');
    }
  };

  if (loading) {
    return (
      <div className="panel" style={styles.panel}>
        <div className="panel-title">📋 方案列表</div>
        <div style={styles.empty}>加载中...</div>
      </div>
    );
  }

  if (scenarios.length === 0) {
    return (
      <div className="panel" style={styles.panel}>
        <div className="panel-title">📋 方案列表</div>
        <div style={styles.empty}>暂无方案，请先运行仿真后保存</div>
      </div>
    );
  }

  return (
    <div className="panel" style={styles.panel}>
      <div className="panel-title">📋 方案列表 ({scenarios.length})</div>
      <div style={styles.list}>
        {scenarios.map((s) => (
          <div
            key={s.id}
            style={{
              ...styles.item,
              backgroundColor: checkedIds.has(s.id) ? 'rgba(24, 144, 255, 0.1)' : 'transparent',
              borderColor: checkedIds.has(s.id) ? 'var(--color-primary)' : 'var(--border-color)',
            }}
          >
            <label style={styles.checkLabel}>
              <input
                type="checkbox"
                checked={checkedIds.has(s.id)}
                onChange={() => onToggle(s.id)}
                style={styles.checkbox}
              />
              <div style={styles.info}>
                <div style={styles.name}>
                  {renaming === s.id ? (
                    <input
                      ref={inputRef}
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={handleSubmitRename}
                      onKeyDown={handleKeyDown}
                      onClick={(e) => e.stopPropagation()}
                      style={styles.renameInput}
                    />
                  ) : (
                    <span
                      onClick={() => handleStartRename(s.id)}
                      style={styles.nameText}
                      title="点击修改方案名称"
                    >
                      {s.name}
                    </span>
                  )}
                </div>
                <div style={styles.meta}>
                  {formatSimTime(s.totalTime)} · {s.avgSpeed.toFixed(1)} km/h · {s.netEnergy.toFixed(1)} kWh
                </div>
              </div>
            </label>
            <div style={styles.actions}>
              <button
                className="btn"
                onClick={() => handleApply(s.id)}
                disabled={isRunning}
                style={styles.actionBtn}
                title="加载方案参数到引擎"
              >
                📥
              </button>
              <button
                className="btn"
                onClick={() => handleDelete(s.id, s.name)}
                style={styles.actionBtn}
                title="删除方案"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 10px',
    border: '1px solid var(--border-color)',
    borderRadius: 'var(--border-radius)',
    transition: 'border-color 0.2s, background-color 0.2s',
  },
  checkLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    flex: 1,
    minWidth: 0,
  },
  checkbox: {
    flexShrink: 0,
  },
  info: {
    minWidth: 0,
  },
  name: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-highlight)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  nameText: {
    cursor: 'pointer',
    borderBottom: '1px dashed var(--text-secondary)',
    paddingBottom: '1px',
  },
  renameInput: {
    width: '100%',
    fontSize: '13px',
    padding: '2px 6px',
    border: '1px solid var(--color-primary)',
    borderRadius: '3px',
    outline: 'none',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    boxSizing: 'border-box' as const,
  },
  meta: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    marginTop: '2px',
  },
  actions: {
    display: 'flex',
    gap: '4px',
    flexShrink: 0,
    marginLeft: '8px',
  },
  actionBtn: {
    fontSize: '14px',
    padding: '4px 6px',
    lineHeight: 1,
  },
  empty: {
    textAlign: 'center',
    color: 'var(--text-secondary)',
    fontSize: '13px',
    padding: '24px 0',
  },
};
