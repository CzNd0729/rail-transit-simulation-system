/**
 * ErrorBoundary — 错误边界组件
 * 捕获子组件的渲染错误，显示错误信息而非白屏
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] 组件渲染错误:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={styles.container}>
          <div style={styles.card}>
            <div style={styles.icon}>⚠️</div>
            <h2 style={styles.title}>页面渲染出错</h2>
            <p style={styles.message}>{this.state.error?.message}</p>
            <pre style={styles.stack}>{this.state.error?.stack}</pre>
            <button
              style={styles.button}
              onClick={() => window.location.reload()}
            >
              刷新页面
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: '100vw',
    height: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0a0a23',
    color: '#e0e0e0',
  },
  card: {
    maxWidth: '600px',
    padding: '32px',
    backgroundColor: '#16213e',
    borderRadius: '8px',
    border: '1px solid #ff4d4f',
    textAlign: 'center',
  },
  icon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  title: {
    fontSize: '20px',
    color: '#ff4d4f',
    marginBottom: '12px',
  },
  message: {
    fontSize: '14px',
    color: '#e0e0e0',
    marginBottom: '16px',
  },
  stack: {
    fontSize: '11px',
    color: '#a0a0a0',
    textAlign: 'left',
    padding: '12px',
    backgroundColor: '#0a0a23',
    borderRadius: '4px',
    overflow: 'auto',
    maxHeight: '200px',
    marginBottom: '16px',
  },
  button: {
    padding: '8px 24px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: '#1890ff',
    color: '#fff',
    fontSize: '14px',
    cursor: 'pointer',
  },
};
