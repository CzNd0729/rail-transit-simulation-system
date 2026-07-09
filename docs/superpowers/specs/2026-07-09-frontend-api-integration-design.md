# 前端 REST API 对接设计

> 日期: 2026-07-09 | 迭代: 一

## 范围

仅前端改动，不修改后端文件。对接三块功能：参数面板提交、CSV 导出、FPS 显示。

## 1. 参数面板对接（UI-PARAM-01/02/05）

### 改动文件
- 新增 `hooks/useParamSubmit.ts`
- 修改 `components/param/ParamPanel.tsx`

### 逻辑
```typescript
// useParamSubmit.ts
export function useParamSubmit() {
  const dispatch = useSimulationDispatch();
  
  const submitParams = async (params: Partial<SimulationParams>) => {
    try {
      const updated = await api.updateParams(params);  // PUT /params
      dispatch({ type: 'UPDATE_PARAMS', payload: updated });
    } catch (err) {
      console.error('参数提交失败:', err);
      // 失败时回滚本地状态（可选）
    }
  };
  
  return { submitParams };
}
```

`ParamPanel.tsx` 中用 `submitParams` 替换现有的仅本地 dispatch 逻辑。

### API 对应
- `PUT /api/v1/params` — 更新运行时参数
- `GET /api/v1/params` — 获取当前参数（初始化时可选调用）

## 2. CSV 导出对接（UI-EXPORT-01）

### 改动文件
- 修改 `components/export/ExportPanel.tsx`

### 逻辑
```typescript
// ExportPanel.tsx
const handleExport = async () => {
  setLoading(true);
  try {
    const csv = await api.exportCSV();  // GET /simulation/export/csv
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `simulation-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('CSV 导出失败:', err);
  } finally {
    setLoading(false);
  }
};
```

### API 对应
- `GET /api/v1/simulation/export/csv` — 返回 CSV 文本

## 3. FPS 实时显示（UI-BAR-02）

### 改动文件
- 新增 `hooks/useFPS.ts`
- 修改 `layouts/StatusBar.tsx`

### 逻辑
```typescript
// useFPS.ts
export function useFPS() {
  const dispatch = useSimulationDispatch();
  
  useEffect(() => {
    let frames = 0;
    let lastTime = performance.now();
    let raf: number;
    
    const tick = (now: number) => {
      frames++;
      if (now - lastTime >= 1000) {
        dispatch({ type: 'SET_FPS', payload: frames });
        frames = 0;
        lastTime = now;
      }
      raf = requestAnimationFrame(tick);
    };
    
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [dispatch]);
}
```

在 `App.tsx` 或 `MainLayout.tsx` 中调用 `useFPS()`。`StatusBar.tsx` 读取 `context.fps` 显示。

## 不修改项

- 后端文件（禁止）
- `SimulationContext.tsx`（已有 SET_FPS action）
- `api.ts`（已有全部 REST 函数）
- `useSimulation.ts` / `useWebSocket.ts`（控制指令走 WebSocket，不改）
