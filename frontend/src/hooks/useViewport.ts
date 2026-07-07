/**
 * useViewport — SVG 视口管理 Hook
 * 管理缩放、平移、跟随模式，输出 viewBox 字符串
 *
 * 坐标系: 世界坐标 (m), X = 公里标, Y = 股道映射
 */
import { useState, useCallback, useRef, useEffect, type RefObject } from 'react';

interface ViewportState {
  zoom: number;
  panX: number;
  panY: number;
  followMode: boolean;
}

interface UseViewportOptions {
  /** 列车当前公里标 (m), undefined 表示无列车 */
  trainPosition?: number;
  /** 线路总长 (m) */
  totalLength: number;
  /** SVG 容器的 ref */
  containerRef: RefObject<SVGSVGElement | null>;
  /** Y 轴可视范围 (世界坐标单位) */
  worldHeight?: number;
  /** 最小缩放 */
  minZoom?: number;
  /** 最大缩放 */
  maxZoom?: number;
}

interface UseViewportReturn {
  /** 当前 SVG viewBox 字符串 */
  viewBox: string;
  /** 当前缩放倍率 */
  zoom: number;
  /** 是否处于跟随模式 */
  followMode: boolean;
  /** 设置缩放倍率 */
  setZoom: (z: number) => void;
  /** 切换跟随模式 */
  toggleFollow: () => void;
  /** 缩放到全线可见 */
  fitAll: () => void;
  /** 滚轮事件处理 */
  handleWheel: (e: React.WheelEvent) => void;
  /** 鼠标按下 (开始拖拽) */
  handleMouseDown: (e: React.MouseEvent) => void;
  /** 鼠标移动 (拖拽中) */
  handleMouseMove: (e: React.MouseEvent) => void;
  /** 鼠标松开 (结束拖拽) */
  handleMouseUp: () => void;
}

export function useViewport(options: UseViewportOptions): UseViewportReturn {
  const {
    trainPosition,
    totalLength,
    containerRef,
    worldHeight = 80,
    minZoom = 0.2,
    maxZoom = 5.0,
  } = options;

  const [state, setState] = useState<ViewportState>({
    zoom: 1.0,
    panX: 0,
    panY: 0,
    followMode: true,
  });

  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const animFrameRef = useRef<number>(0);

  // 计算容器宽度 (px)
  const getContainerWidth = useCallback(() => {
    return containerRef.current?.clientWidth || 800;
  }, [containerRef]);

  // 计算 viewBox 宽度 (世界坐标)
  const getViewWidth = useCallback((zoom: number) => {
    return totalLength / zoom;
  }, [totalLength]);

  // 屏幕像素 → 世界坐标 X
  const screenToWorldX = useCallback((screenX: number, zoom: number, panX: number) => {
    const containerW = getContainerWidth();
    const viewW = totalLength / zoom;
    return panX + (screenX / containerW) * viewW;
  }, [getContainerWidth, totalLength]);

  // 跟随模式: 更新 panX 使列车在视口 30% 处
  useEffect(() => {
    if (!state.followMode || trainPosition === undefined) return;

    const viewW = getViewWidth(state.zoom);
    const targetPanX = trainPosition - viewW * 0.3;
    const clampedPanX = Math.max(0, Math.min(targetPanX, totalLength - viewW));

    setState(prev => {
      if (Math.abs(prev.panX - clampedPanX) < 0.5) return prev;
      return { ...prev, panX: clampedPanX };
    });
  }, [trainPosition, state.followMode, state.zoom, getViewWidth, totalLength]);

  // 计算 viewBox 字符串
  const viewW = getViewWidth(state.zoom);
  const clampedPanX = Math.max(0, Math.min(state.panX, Math.max(0, totalLength - viewW)));
  const viewBox = `${clampedPanX} ${state.panY} ${viewW} ${worldHeight}`;

  // 缩放
  const setZoom = useCallback((z: number) => {
    setState(prev => ({ ...prev, zoom: Math.max(minZoom, Math.min(maxZoom, z)) }));
  }, [minZoom, maxZoom]);

  // 切换跟随
  const toggleFollow = useCallback(() => {
    setState(prev => {
      if (!prev.followMode && trainPosition !== undefined) {
        // 重新锁定: 平滑动画到列车位置
        const viewW = totalLength / prev.zoom;
        const targetPanX = trainPosition - viewW * 0.3;
        const clamped = Math.max(0, Math.min(targetPanX, totalLength - viewW));

        const startPanX = prev.panX;
        const startTime = performance.now();
        const duration = 300;

        const animate = (now: number) => {
          const t = Math.min((now - startTime) / duration, 1);
          const eased = t * (2 - t); // ease-out
          const currentPanX = startPanX + (clamped - startPanX) * eased;
          setState(s => ({ ...s, panX: currentPanX }));
          if (t < 1) {
            animFrameRef.current = requestAnimationFrame(animate);
          }
        };
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = requestAnimationFrame(animate);

        return { ...prev, followMode: true };
      }
      return { ...prev, followMode: false };
    });
  }, [trainPosition, totalLength]);

  // 全线总览
  const fitAll = useCallback(() => {
    setState(prev => ({ ...prev, zoom: minZoom, panX: 0, panY: 0, followMode: false }));
  }, [minZoom]);

  // 滚轮缩放: 以鼠标位置为锚点
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = e.clientX - rect.left;
    setState(prev => {
      const worldXBefore = screenToWorldX(mouseX, prev.zoom, prev.panX);
      const delta = e.deltaY > 0 ? -0.2 : 0.2;
      const newZoom = Math.max(minZoom, Math.min(maxZoom, prev.zoom + delta));
      const containerW = getContainerWidth();
      const newViewW = totalLength / newZoom;
      const newPanX = worldXBefore - (mouseX / containerW) * newViewW;
      return { ...prev, zoom: newZoom, panX: newPanX, followMode: false };
    });
  }, [containerRef, screenToWorldX, minZoom, maxZoom, getContainerWidth, totalLength]);

  // 鼠标拖拽
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    dragStart.current = { x: e.clientX, y: e.clientY, panX: state.panX, panY: state.panY };
    setState(prev => ({ ...prev, followMode: false }));
  }, [state.panX, state.panY]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging.current) return;
    const containerW = getContainerWidth();
    setState(prev => {
      const viewW = totalLength / prev.zoom;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      const worldDx = -(dx / containerW) * viewW;
      const worldDy = -(dy / containerW) * viewW;
      return {
        ...prev,
        panX: dragStart.current.panX + worldDx,
        panY: dragStart.current.panY + worldDy,
      };
    });
  }, [getContainerWidth, totalLength]);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  // 清理动画帧
  useEffect(() => {
    return () => cancelAnimationFrame(animFrameRef.current);
  }, []);

  return {
    viewBox,
    zoom: state.zoom,
    followMode: state.followMode,
    setZoom,
    toggleFollow,
    fitAll,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
  };
}
