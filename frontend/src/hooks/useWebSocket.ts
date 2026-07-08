import { useEffect, useRef, useCallback } from 'react';
import { WS_BASE_URL, WS_RECONNECT_INTERVAL, USE_MOCK } from '../utils/constants';
import { useSimulationDispatch } from '../context/SimulationContext';
import { parseServerSnapshot, parseSimulationSummary } from '../utils/apiAdapter';
import type { ServerMessage } from '../types/simulation';

/**
 * WebSocket 连接管理
 * @param url WebSocket 服务地址，默认使用环境变量或 localhost
 */
export function useWebSocket(url: string = WS_BASE_URL) {
  const dispatch = useSimulationDispatch();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    dispatch({ type: 'WS_CONNECTING' });

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        dispatch({ type: 'WS_CONNECTED' });
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ServerMessage;

          switch (message.type) {
            case 'simulation_snapshot':
              dispatch({
                type: 'RUNTIME_UPDATE',
                payload: parseServerSnapshot(message.data),
              });
              break;
            case 'simulation_status':
              dispatch({ type: 'SET_RUN_STATE', payload: message.data.runState });
              break;
            case 'simulation_complete': {
              dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
              const summary = (message.data as Record<string, unknown>)?.summary;
              if (summary && typeof summary === 'object') {
                dispatch({
                  type: 'SET_STATS',
                  payload: parseSimulationSummary(summary as Record<string, unknown>),
                });
              }
              break;
            }
            case 'init_state':
              if (message.state?.runState) {
                dispatch({ type: 'SET_RUN_STATE', payload: message.state.runState });
              }
              break;
            default:
              break;
          }
        } catch (err) {
          console.error('[WebSocket] 消息解析失败:', err);
        }
      };

      ws.onclose = () => {
        dispatch({ type: 'WS_DISCONNECTED' });
        reconnectTimer.current = setTimeout(connect, WS_RECONNECT_INTERVAL);
      };

      ws.onerror = (err) => {
        console.error('[WebSocket] 连接错误:', err);
        ws.close();
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WebSocket] 创建连接失败:', err);
      reconnectTimer.current = setTimeout(connect, WS_RECONNECT_INTERVAL);
    }
  }, [url, dispatch]);

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] 连接未就绪，无法发送消息');
    }
  }, []);

  useEffect(() => {
    if (USE_MOCK) return;
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
    };
  }, [connect]);

  return { send };
}
