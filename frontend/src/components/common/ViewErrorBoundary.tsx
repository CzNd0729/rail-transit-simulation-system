import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  viewKey: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/** 视图级错误边界：单页崩溃不拖垮整应用 */
export default class ViewErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[ViewErrorBoundary:${this.props.viewKey}]`, error, errorInfo);
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.viewKey !== this.props.viewKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: 24,
            color: '#ff4d4f',
            background: '#0a0a23',
            height: '100%',
          }}
        >
          <h3>视图渲染出错</h3>
          <p style={{ color: '#e0e0e0' }}>{this.state.error?.message}</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            重试
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
