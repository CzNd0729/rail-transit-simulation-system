/**
 * WebSocket 连接管理 Hook
 * 基于《详细设计文档》5.3 WebSocket 连接管理设计
 * 功能：自动连接、断线重连、消息分发
 */
import { useEffect, useRef, useCallback } from 'react';
import { WS_BASE_URL, WS_RECONNECT_INTERVAL } from '../utils/constants';
import { useSimulationDispatch } from '../context/SimulationContext';
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
          const message: ServerMessage = JSON.parse(event.data);

          if (message.type === 'simulation_snapshot') {
            dispatch({
              type: 'RUNTIME_UPDATE',
              payload: message.data,
            });
          }
          // init_state 消息可在后续扩展处理
        } catch (err) {
          console.error('[WebSocket] 消息解析失败:', err);
        }
      };

      ws.onclose = () => {
        dispatch({ type: 'WS_DISCONNECTED' });
        // 自动重连
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

  /** 发送消息到服务端 */
  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] 连接未就绪，无法发送消息');
    }
  }, []);

  useEffect(() => {
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
