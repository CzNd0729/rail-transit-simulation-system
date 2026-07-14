/**
 * ScenarioComparePage — 方案对比页面
 * 基于《多方案对比决策功能设计文档》4.1 页面结构
 *
 * 布局：左侧方案管理 + 右侧 Tab 切换（指标对比 / 参数对比）
 */
import { useState, useEffect, useCallback } from 'react';
import { getScenarios, getScenario } from '../services/api';
import ScenarioListPanel from '../components/scenario/ScenarioListPanel';
import CompareTable from '../components/scenario/CompareTable';
import CompareChartBar from '../components/scenario/CompareChartBar';
import CompareParams from '../components/scenario/CompareParams';
import type { ScenarioSummary, ScenarioDetailResponse } from '../types/simulation';

type CompareTab = 'metrics' | 'params';

export default function ScenarioComparePage() {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [details, setDetails] = useState<ScenarioDetailResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<CompareTab>('metrics');
  const [autoSavedInfo, setAutoSavedInfo] = useState<{ id: string; name: string } | null>(null);

  /** 加载方案列表 */
  const loadScenarios = useCallback(async () => {
    setLoading(true);
    try {
      const list = await getScenarios();
      setScenarios(Array.isArray(list) ? list : []);
    } catch {
      setScenarios([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadScenarios();
  }, [loadScenarios]);

  /** 自动保存完成后刷新方案列表并显示提示 */
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setAutoSavedInfo({ id: detail.id, name: detail.name });
      loadScenarios();
    };
    window.addEventListener('scenario-auto-saved', handler);
    return () => window.removeEventListener('scenario-auto-saved', handler);
  }, [loadScenarios]);

  /** 自动保存提示 15s 后自动消失 */
  useEffect(() => {
    if (!autoSavedInfo) return;
    const timer = setTimeout(() => setAutoSavedInfo(null), 15000);
    return () => clearTimeout(timer);
  }, [autoSavedInfo]);

  /** 选中方案变化时，重新加载详情（支持 1+ 个方案） */
  useEffect(() => {
    if (checkedIds.size < 1) {
      setDetails([]);
      return;
    }
    let cancelled = false;
    const loadDetails = async () => {
      setDetailsLoading(true);
      const results: ScenarioDetailResponse[] = [];
      for (const id of checkedIds) {
        if (cancelled) break;
        try {
          const detail = await getScenario(id);
          results.push(detail);
        } catch {
          // 跳过损坏的方案
        }
      }
      if (!cancelled) {
        setDetails(results);
        setDetailsLoading(false);
      }
    };
    loadDetails();
    return () => { cancelled = true; };
  }, [checkedIds]);

  /** 勾选/取消方案 */
  const handleToggle = (id: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div style={styles.container}>
      {/* 左侧：方案管理 */}
      <div style={styles.leftPanel}>
        <ScenarioListPanel
          scenarios={scenarios}
          checkedIds={checkedIds}
          onToggle={handleToggle}
          onDeleted={loadScenarios}
          onApplied={() => {
            window.dispatchEvent(new CustomEvent('scenario-applied'));
          }}
          loading={loading}
        />
      </div>

      {/* 右侧：对比视图 */}
      <div style={styles.rightPanel}>

        {/* 自动保存完成通知条 */}
        {autoSavedInfo && (
          <div style={styles.autoSaveNotice}>
            <span>💾 方案已自动保存</span>
            <span style={{ marginLeft: '8px' }}>
              点击「{autoSavedInfo.name}」名称可修改方案名
            </span>
            <button
              className="btn"
              style={{ marginLeft: 'auto', fontSize: '12px', padding: '2px 8px' }}
              onClick={() => setAutoSavedInfo(null)}
            >
              ✕
            </button>
          </div>
        )}

        {/* Tab 切换 */}
        <div style={styles.tabBar}>
          <button
            className={`btn ${activeTab === 'metrics' ? 'btn-primary' : ''}`}
            onClick={() => setActiveTab('metrics')}
            style={styles.tabBtn}
          >
            📊 指标对比
          </button>
          <button
            className={`btn ${activeTab === 'params' ? 'btn-primary' : ''}`}
            onClick={() => setActiveTab('params')}
            style={styles.tabBtn}
          >
            🔧 参数对比
          </button>
        </div>

        {detailsLoading ? (
          <div className="panel" style={styles.loadingPanel}>
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px 0' }}>
              加载方案详情中...
            </div>
          </div>
        ) : activeTab === 'metrics' ? (
          <>
            <CompareTable scenarios={details} />
            <div style={styles.chartArea}>
              <CompareChartBar scenarios={details} />
            </div>
          </>
        ) : (
          <CompareParams scenarios={details} />
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    height: '100%',
    gap: '12px',
    minHeight: 0,
  },
  leftPanel: {
    width: '300px',
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
    overflowY: 'auto',
  },
  rightPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
    minHeight: 0,
    overflowY: 'auto',
  },
  chartArea: {
    flex: 1,
    minHeight: '250px',
  },
  loadingPanel: {
    flex: 1,
  },
  autoSaveNotice: {
    display: 'flex',
    alignItems: 'center',
    padding: '8px 16px',
    marginBottom: '12px',
    backgroundColor: 'rgba(24, 144, 255, 0.1)',
    border: '1px solid var(--color-primary)',
    borderRadius: 'var(--border-radius)',
    fontSize: '13px',
    color: 'var(--color-primary)',
    flexShrink: 0,
  },
  tabBar: {
    display: 'flex',
    gap: '8px',
    marginBottom: '12px',
    flexShrink: 0,
  },
  tabBtn: {
    fontSize: '13px',
    padding: '6px 16px',
  },
};
