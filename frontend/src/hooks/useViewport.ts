/**
 * useViewport — SVG 视口管理 Hook
 * 管理缩放、水平平移、跟随模式，输出 viewBox 字符串
 *
 * 坐标系: 世界坐标 (m), X = 公里标, Y = 固定
 * 仅支持水平方向拖拽，Y 轴固定
 */
import { useState, useCallback, useRef, useEffect, type RefObject } from 'react';

/** 解析 useViewport 输出的 viewBox 字符串 */
export function parseViewBox(viewBox: string): { panX: number; viewW: number } {
  const [panX = 0, , viewW = 0] = viewBox.split(' ').map(Number);
  return { panX, viewW };
}

/** 将 panX 限制在 [0, totalLength - viewW] 内，避免视口超出线路范围 */
export function clampPanX(panX: number, viewW: number, totalLength: number): number {
  if (totalLength <= 0 || viewW >= totalLength) return 0;
  return Math.max(0, Math.min(panX, totalLength - viewW));
}

interface ViewportState {
  zoom: number;
  panX: number;
  followMode: boolean;
}

interface UseViewportOptions {
  trainPosition?: number;
  totalLength: number;
  containerRef: RefObject<SVGSVGElement | HTMLElement | null>;
  worldHeight?: number;
  maxZoom?: number;
  /** 初始缩放倍率，默认 1（全线）；>1 为局部放大 */
  initialZoom?: number;
  /** 初始是否锁定跟随列车，默认 true */
  initialFollowMode?: boolean;
  /** 是否限制平移不超出 [0, totalLength]，默认 false（线路图端点可留白） */
  clampPan?: boolean;
}

interface UseViewportReturn {
  viewBox: string;
  zoom: number;
  followMode: boolean;
  setZoom: (z: number) => void;
  toggleFollow: () => void;
  fitAll: () => void;
  focusPosition: (worldX: number, targetZoom: number, duration?: number) => void;
  handleWheel: (e: WheelEvent) => void;
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
    maxZoom: maxZoomProp,
    initialZoom = 1.0,
    initialFollowMode = true,
    clampPan = false,
  } = options;

  // 动态计算 maxZoom：根据轨道总长，确保能看清细节
  // 18.6km 轨道，maxZoom ≈ 18.6；3.2km 轨道，maxZoom ≈ 5
  const maxZoom = maxZoomProp ?? Math.max(5, Math.min(30, totalLength / 1000));
  const minZoom = 1.0;

  // 初始 zoom：如果 initialZoom 为默认值 1.0，则根据容器宽度动态计算
  const [state, setState] = useState<ViewportState>(() => {
    let zoom = initialZoom;
    if (initialZoom === 1.0) {
      const containerWidth = containerRef.current?.clientWidth ?? 800;
      zoom = Math.max(minZoom, containerWidth / totalLength);
    }
    const clampedZoom = Math.max(minZoom, Math.min(maxZoom, zoom));
    const viewW = totalLength / clampedZoom;
    return {
      zoom: clampedZoom,
      panX: clampPan ? Math.max(0, Math.min(0, totalLength - viewW)) : 0,
      followMode: initialFollowMode,
    };
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

  const applyPan = useCallback((panX: number, zoom: number) => {
    if (!clampPan) return panX;
    return clampPanX(panX, totalLength / zoom, totalLength);
  }, [clampPan, totalLength]);

  // 平滑动画: 从当前状态过渡到目标 (通过 ref 读取最新值)
  const animateTo = useCallback((targetPanX: number, targetZoom: number, duration = 300) => {
    cancelAnimationFrame(animFrameRef.current);
    setIsAnimating(true);

    const clampedTargetPanX = applyPan(targetPanX, targetZoom);
    const startPanX = stateRef.current.panX;
    const startZoom = stateRef.current.zoom;
    const startTime = performance.now();

    const animate = (now: number) => {
      const t = Math.min((now - startTime) / duration, 1);
      const eased = t * (2 - t);

      const currentZoom = startZoom + (targetZoom - startZoom) * eased;
      const rawPanX = startPanX + (clampedTargetPanX - startPanX) * eased;
      const currentPanX = applyPan(rawPanX, currentZoom);

      setState(prev => ({ ...prev, panX: currentPanX, zoom: currentZoom }));

      if (t < 1) {
        animFrameRef.current = requestAnimationFrame(animate);
      } else {
        setIsAnimating(false);
      }
    };

    animFrameRef.current = requestAnimationFrame(animate);
  }, [applyPan]);

  // 跟随模式
  useEffect(() => {
    if (!state.followMode || trainPosition === undefined || isAnimating) return;

    const followZoom = Math.max(state.zoom, 2.0);
    const viewW = getViewWidth(followZoom);
    const rawTargetPanX = trainPosition - viewW * 0.5;
    const targetPanX = clampPan ? clampPanX(rawTargetPanX, viewW, totalLength) : rawTargetPanX;

    setState(prev => {
      if (Math.abs(prev.panX - targetPanX) < 0.5 && Math.abs(prev.zoom - followZoom) < 0.01) return prev;
      return { ...prev, panX: targetPanX, zoom: followZoom };
    });
  }, [trainPosition, state.followMode, state.zoom, getViewWidth, totalLength, isAnimating, clampPan]);

  // viewBox 字符串 (跟随模式下不 clamp，允许端点外空白)
  const viewW = getViewWidth(state.zoom);
  const viewBox = `${state.panX} 0 ${viewW} ${worldHeight}`;

  const setZoom = useCallback((z: number) => {
    setState(prev => {
      const newZoom = Math.max(minZoom, Math.min(maxZoom, z));
      return {
        ...prev,
        zoom: newZoom,
        panX: applyPan(prev.panX, newZoom),
      };
    });
  }, [minZoom, maxZoom, applyPan]);

  const toggleFollow = useCallback(() => {
    const cur = stateRef.current;
    if (!cur.followMode && trainPosition !== undefined) {
      setState(prev => ({ ...prev, followMode: true }));
      const viewW = totalLength / cur.zoom;
      const targetPanX = trainPosition - viewW * 0.5;
      const clamped = clampPan
        ? clampPanX(targetPanX, viewW, totalLength)
        : targetPanX;
      animateTo(clamped, cur.zoom, 300);
    } else {
      setState(prev => ({ ...prev, followMode: false }));
    }
  }, [trainPosition, totalLength, animateTo, clampPan]);

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
    const clampedPanX = clampPan ? clampPanX(targetPanX, viewW, totalLength) : targetPanX;

    setState(prev => ({ ...prev, followMode: false }));
    animateTo(clampedPanX, clampedZoom, duration);
  }, [minZoom, maxZoom, totalLength, animateTo, clampPan]);

  // 滚轮缩放 — 通过原生事件绑定避免 passive 警告
  const handleWheel = useCallback((e: WheelEvent) => {
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
      return {
        ...prev,
        zoom: newZoom,
        panX: applyPan(newPanX, newZoom),
        followMode: false,
      };
    });
  }, [containerRef, screenToWorldX, minZoom, maxZoom, getContainerWidth, totalLength, applyPan]);

  // 原生事件绑定 — 绕过 React 默认 passive 限制
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('wheel', handleWheel as unknown as EventListener, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel as unknown as EventListener);
  }, [containerRef, handleWheel]);

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
      const rawPanX = dragStart.current.panX + worldDx;
      return { ...prev, panX: applyPan(rawPanX, prev.zoom) };
    });
  }, [getContainerWidth, totalLength, applyPan]);

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
