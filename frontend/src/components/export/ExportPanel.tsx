/**
 * ExportPanel — 数据导出面板
 */
import { exportCSV } from '../../services/api';
import { useSimulationState } from '../../context/SimulationContext';
import { USE_MOCK } from '../../utils/constants';
import { chartHistoryToCsv, getAllTrainHistories } from '../../utils/chartHistoryExport';
import RunSummaryPanel from './RunSummaryPanel';

function downloadCsv(csvData: string) {
  const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `simulation_data_${Date.now()}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export default function ExportPanel() {
  const { chartHistory } = useSimulationState();

  const handleExportCSV = async () => {
    try {
      if (USE_MOCK) {
        if (getAllTrainHistories(chartHistory).length === 0) {
          alert('暂无仿真数据，请先运行仿真');
          return;
        }
        downloadCsv(chartHistoryToCsv(chartHistory));
        return;
      }
      const csvData = await exportCSV();
      downloadCsv(csvData);
    } catch (err) {
      console.error('CSV 导出失败:', err);
      alert('CSV 导出失败，请确保仿真已结束');
    }
  };

  return (
    <>
      <RunSummaryPanel />
      <div className="panel">
        <div className="panel-title">📥 数据导出</div>
        <div style={styles.content}>
          <button className="btn" onClick={handleExportCSV} style={styles.btn}>
            📥 导出 CSV
          </button>

          <button className="btn" disabled style={styles.btn}>
            📊 导出截图（迭代二）
          </button>

          <button className="btn" disabled style={styles.btn}>
            📄 导出报告（迭代四）
          </button>
        </div>
      </div>
    </>
  );
}

const styles: Record<string, React.CSSProperties> = {
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  btn: {
    width: '100%',
    padding: '8px 0',
    fontSize: '12px',
  },
};
