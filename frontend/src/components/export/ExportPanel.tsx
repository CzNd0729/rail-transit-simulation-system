/**
 * ExportPanel — 数据导出面板
 * 基于《需求文档》3.4.3 数据导出区设计
 *
 * 功能：
 * - UI-EXPORT-01: 导出 CSV — 导出当前仿真运行数据
 * - UI-EXPORT-02: 导出截图 — 导出当前视图为 PNG 图片（迭代二）
 * - UI-EXPORT-03: 导出运行报告 — 生成 PDF 格式的仿真运行报告（迭代四）
 */
import { exportCSV } from '../../services/api';

export default function ExportPanel() {
  const handleExportCSV = async () => {
    try {
      const csvData = await exportCSV();
      const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `simulation_data_${Date.now()}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('CSV 导出失败:', err);
      alert('CSV 导出失败，请确保仿真已结束');
    }
  };

  return (
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
