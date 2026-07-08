/**
 * useViewport — SVG 视口管理 Hook
 * 管理缩放、水平平移、跟随模式，输出 viewBox 字符串
 *
 * 坐标系: 世界坐标 (m), X = 公里标, Y = 固定
 * 仅支持水平方向拖拽，Y 轴固定
 */
import { useState, useCallback, useRef, useEffect, type RefObject } from 'react';

interface ViewportState {
  zoom: number;
  panX: number;
  followMode: boolean;
}

interface UseViewportOptions {
  trainPosition?: number;
  totalLength: number;
  containerRef: RefObject<SVGSVGElement | null>;
  worldHeight?: number;
  maxZoom?: number;
}

interface UseViewportReturn {
  viewBox: string;
  zoom: number;
  followMode: boolean;
  setZoom: (z: number) => void;
  toggleFollow: () => void;
  fitAll: () => void;
  focusPosition: (worldX: number, targetZoom: number, duration?: number) => void;
  handleWheel: (e: React.WheelEvent) => void;
  handleMouseDown: (e: React.MouseEvent) => void;
  handleMouseMove: (e: React.MouseEvent) => void;
  handleMouseUp: () => void;
  isAnimating: boolean;
}

export function useViewport(options: UseViewportOptions): UseViewportReturn {
  const {
    trainPosition,
    totalLength,
    containerRef,
    worldHeight = 80,
    maxZoom = 5.0,
  } = options;

  const minZoom = 1.0;

  const [state, setState] = useState<ViewportState>({
    zoom: 1.0,
    panX: 0,
    followMode: true,
  });
  const [isAnimating, setIsAnimating] = useState(false);

  // 用 ref 追踪最新状态，供动画闭包读取
  const stateRef = useRef(state);
  stateRef.current = state;

  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, panX: 0 });
  const animFrameRef = useRef<number>(0);

  const getContainerWidth = useCallback(() => {
    return containerRef.current?.clientWidth || 800;
  }, [containerRef]);

  const getViewWidth = useCallback((zoom: number) => {
    return totalLength / zoom;
  }, [totalLength]);

  const screenToWorldX = useCallback((screenX: number, zoom: number, panX: number) => {
    const containerW = getContainerWidth();
    const viewW = totalLength / zoom;
    return panX + (screenX / containerW) * viewW;
  }, [getContainerWidth, totalLength]);

  // 平滑动画: 从当前状态过渡到目标 (通过 ref 读取最新值)
  const animateTo = useCallback((targetPanX: number, targetZoom: number, duration = 300) => {
    cancelAnimationFrame(animFrameRef.current);
    setIsAnimating(true);

    // 从 ref 读取当前最新值作为起点
    const startPanX = stateRef.current.panX;
    const startZoom = stateRef.current.zoom;
    const startTime = performance.now();

    const animate = (now: number) => {
      const t = Math.min((now - startTime) / duration, 1);
      const eased = t * (2 - t);

      const currentPanX = startPanX + (targetPanX - startPanX) * eased;
      const currentZoom = startZoom + (targetZoom - startZoom) * eased;

      setState(prev => ({ ...prev, panX: currentPanX, zoom: currentZoom }));

      if (t < 1) {
        animFrameRef.current = requestAnimationFrame(animate);
      } else {
        setIsAnimating(false);
      }
    };

    animFrameRef.current = requestAnimationFrame(animate);
  }, []); // 无依赖: 始终通过 stateRef 读取

  // 跟随模式
  useEffect(() => {
    if (!state.followMode || trainPosition === undefined || isAnimating) return;

    const followZoom = Math.max(state.zoom, 2.0);
    const viewW = getViewWidth(followZoom);
    // 列车始终居中，不 clamp：端点处允许视口超出轨道边界
    const targetPanX = trainPosition - viewW * 0.5;

    setState(prev => {
      if (Math.abs(prev.panX - targetPanX) < 0.5 && Math.abs(prev.zoom - followZoom) < 0.01) return prev;
      return { ...prev, panX: targetPanX, zoom: followZoom };
    });
  }, [trainPosition, state.followMode, state.zoom, getViewWidth, totalLength, isAnimating]);

  // viewBox 字符串 (跟随模式下不 clamp，允许端点外空白)
  const viewW = getViewWidth(state.zoom);
  const viewBox = `${state.panX} 0 ${viewW} ${worldHeight}`;

  const setZoom = useCallback((z: number) => {
    setState(prev => ({ ...prev, zoom: Math.max(minZoom, Math.min(maxZoom, z)) }));
  }, [minZoom, maxZoom]);

  const toggleFollow = useCallback(() => {
    const cur = stateRef.current;
    if (!cur.followMode && trainPosition !== undefined) {
      setState(prev => ({ ...prev, followMode: true }));
      const viewW = totalLength / cur.zoom;
      const targetPanX = trainPosition - viewW * 0.5;
      const clamped = Math.max(0, Math.min(targetPanX, totalLength - viewW));
      animateTo(clamped, cur.zoom, 300);
    } else {
      setState(prev => ({ ...prev, followMode: false }));
    }
  }, [trainPosition, totalLength, animateTo]);

  const fitAll = useCallback(() => {
    cancelAnimationFrame(animFrameRef.current);
    setIsAnimating(false);
    setState({ zoom: minZoom, panX: 0, followMode: false });
  }, [minZoom]);

  // 平滑聚焦到指定位置
  const focusPosition = useCallback((worldX: number, targetZoom: number, duration = 300) => {
    const clampedZoom = Math.max(minZoom, Math.min(maxZoom, targetZoom));
    const viewW = totalLength / clampedZoom;
    const targetPanX = worldX - viewW * 0.5;
    const clampedPanX = Math.max(0, Math.min(targetPanX, totalLength - viewW));

    setState(prev => ({ ...prev, followMode: false }));
    animateTo(clampedPanX, clampedZoom, duration);
  }, [minZoom, maxZoom, totalLength, animateTo]);

  // 滚轮缩放
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

  // 鼠标拖拽: 仅水平
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    dragStart.current = { x: e.clientX, panX: stateRef.current.panX };
    setState(prev => ({ ...prev, followMode: false }));
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging.current) return;
    const containerW = getContainerWidth();
    setState(prev => {
      const viewW = totalLength / prev.zoom;
      const dx = e.clientX - dragStart.current.x;
      const worldDx = -(dx / containerW) * viewW;
      return { ...prev, panX: dragStart.current.panX + worldDx };
    });
  }, [getContainerWidth, totalLength]);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

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
    focusPosition,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    isAnimating,
  };
}
