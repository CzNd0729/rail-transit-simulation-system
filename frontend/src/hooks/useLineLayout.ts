import { useEffect } from 'react';
import { useSimulationDispatch, useSimulationState } from '../context/SimulationContext';
import { getLineConfig } from '../services/api';
import { parseApiLineConfig } from '../utils/lineLayoutAdapter';
import { buildMvpLineLayout, buildProfileSegments } from '../data/mvpLineLayout';
import { USE_MOCK } from '../utils/constants';

export function useLineLayout() {
  const dispatch = useSimulationDispatch();
  const { lineLayout, params } = useSimulationState();

  // Live: 首次加载线路
  useEffect(() => {
    if (USE_MOCK || lineLayout) return;

    getLineConfig()
      .then((raw) => {
        const { layout, profileSegments } = parseApiLineConfig(raw as Record<string, unknown>);
        dispatch({ type: 'SET_LINE_LAYOUT', payload: { layout, profileSegments } });
      })
      .catch((err) => {
        console.warn('[LineLayout] 无法加载后端线路，使用 MVP 默认', err);
        const gradient = params.track.gradient;
        dispatch({
          type: 'SET_LINE_LAYOUT',
          payload: {
            layout: buildMvpLineLayout(gradient),
            profileSegments: buildProfileSegments(gradient),
          },
        });
      });
  }, [dispatch, lineLayout, params.track.gradient]);

  // Mock: 初始化 + 坡度参数变化时重建（场景 2）
  useEffect(() => {
    if (!USE_MOCK) return;
    const gradient = params.track.gradient;
    dispatch({
      type: 'SET_LINE_LAYOUT',
      payload: {
        layout: buildMvpLineLayout(gradient),
        profileSegments: buildProfileSegments(gradient),
      },
    });
  }, [dispatch, params.track.gradient]);
}
