/**
 * ScenarioSavePanel — 保存方案面板
 * 输入名称和描述，保存当前仿真参数+结果为方案
 */
import { useState } from 'react';
import { useSimulationState } from '../../context/SimulationContext';
import { saveScenario } from '../../services/api';

interface ScenarioSavePanelProps {
  onSaved: () => void;
}

export default function ScenarioSavePanel({ onSaved }: ScenarioSavePanelProps) {
  const { runState } = useSimulationState();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const isRunning = runState === 'running';
  const isIdle = runState === 'idle';

  const handleSave = async () => {
    if (!name.trim()) {
      setMessage({ text: '请输入方案名称', ok: false });
      return;
    }
    if (isRunning) {
      setMessage({ text: '请先暂停或停止仿真', ok: false });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await saveScenario(name.trim(), description.trim() || undefined);
      setMessage({ text: `方案「${name.trim()}」保存成功`, ok: true });
      setName('');
      setDescription('');
      onSaved();
    } catch {
      setMessage({ text: '保存失败，请确保已运行过仿真', ok: false });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="panel" style={styles.panel}>
      <div className="panel-title">💾 保存方案</div>

      <div style={styles.field}>
        <label style={styles.label}>方案名称</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例如：ATO经济模式"
          style={styles.input}
          disabled={saving}
        />
      </div>

      <div style={styles.field}>
        <label style={styles.label}>描述（可选）</label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="简述方案特点"
          style={styles.input}
          disabled={saving}
        />
      </div>

      <button
        className="btn btn-primary"
        onClick={handleSave}
        disabled={saving || isIdle}
        style={styles.saveBtn}
      >
        {saving ? '保存中...' : '💾 保存方案'}
      </button>

      {isIdle && !message && (
        <div style={styles.hint}>请先运行一次仿真后再保存</div>
      )}

      {message && (
        <div style={{ ...styles.message, color: message.ok ? 'var(--color-success)' : 'var(--color-error)' }}>
          {message.text}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    marginBottom: '12px',
  },
  field: {
    marginBottom: '10px',
  },
  label: {
    display: 'block',
    marginBottom: '4px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
  input: {
    width: '100%',
  },
  saveBtn: {
    width: '100%',
    marginTop: '4px',
  },
  hint: {
    marginTop: '8px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    textAlign: 'center',
  },
  message: {
    marginTop: '8px',
    fontSize: '12px',
    textAlign: 'center',
  },
};
