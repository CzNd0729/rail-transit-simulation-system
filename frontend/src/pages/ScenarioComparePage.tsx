/**
 * ScenarioComparePage — 方案对比页面
 * 基于《多方案对比决策功能设计文档》4.1 页面结构
 *
 * 布局：左侧方案管理 + 右侧对比视图
 */
import { useState, useEffect, useCallback } from 'react';
import { getScenarios, getScenario } from '../services/api';
import ScenarioSavePanel from '../components/scenario/ScenarioSavePanel';
import ScenarioListPanel from '../components/scenario/ScenarioListPanel';
import CompareTable from '../components/scenario/CompareTable';
import CompareChartBar from '../components/scenario/CompareChartBar';
import type { ScenarioSummary, ScenarioDetailResponse } from '../types/simulation';

export default function ScenarioComparePage() {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [details, setDetails] = useState<ScenarioDetailResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);

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

  /** 选中方案变化时，重新加载详情 */
  useEffect(() => {
    if (checkedIds.size < 2) {
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
        <ScenarioSavePanel onSaved={loadScenarios} />
        <ScenarioListPanel
          scenarios={scenarios}
          checkedIds={checkedIds}
          onToggle={handleToggle}
          onDeleted={loadScenarios}
          onApplied={() => {
            // 应用方案后，刷新参数面板
            window.dispatchEvent(new CustomEvent('scenario-applied'));
          }}
          loading={loading}
        />
      </div>

      {/* 右侧：对比视图 */}
      <div style={styles.rightPanel}>
        {detailsLoading ? (
          <div className="panel" style={styles.loadingPanel}>
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px 0' }}>
              加载方案详情中...
            </div>
          </div>
        ) : (
          <>
            <CompareTable scenarios={details} />
            <div style={styles.chartArea}>
              <CompareChartBar scenarios={details} />
            </div>
          </>
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
};
