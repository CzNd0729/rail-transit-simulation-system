/**
 * REST API 请求封装
 * 基于《详细设计文档》6.3 REST API 概览
 */
import { API_BASE_URL } from '../utils/constants';
import type {
  SimulationConfig,
  VehicleParams,
  ParameterPreset,
  SimulationParams,
  SpeedMultiplier,
  ScenarioSummary,
  ScenarioSaveResponse,
  ScenarioDetailResponse,
} from '../types/simulation';

const BASE = `${API_BASE_URL}/api/v1`;

interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

/** 通用请求封装 */
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText} at ${path}`);
  }
  return res.json();
}

/** 解包 { code, data } 响应 */
async function requestData<T>(path: string, options?: RequestInit): Promise<T> {
  const envelope = await request<ApiEnvelope<T>>(path, options);
  return envelope.data;
}

// ==================== 配置管理 ====================

/** 获取当前仿真配置 */
export async function getConfig(): Promise<SimulationConfig> {
  return request<SimulationConfig>('/config');
}

/** 更新仿真配置 */
export async function updateConfig(config: Partial<SimulationConfig>): Promise<SimulationConfig> {
  return request<SimulationConfig>('/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

/** 获取线路配置 */
export async function getLineConfig() {
  return requestData<Record<string, unknown>>('/config/line');
}

/** 获取车辆配置 */
export async function getVehicleConfig(): Promise<VehicleParams> {
  return request<VehicleParams>('/config/vehicle');
}

// ==================== 仿真控制 ====================

/** 获取仿真运行状态 */
export async function getSimulationStatus() {
  return request('/simulation/status');
}

/** 启动仿真 (REST 备用，优先用 WebSocket) */
export async function startSimulation() {
  return request('/simulation/start', { method: 'POST' });
}

/** 停止仿真 */
export async function stopSimulation() {
  return request('/simulation/stop', { method: 'POST' });
}

/** 单步执行 */
export async function stepSimulation() {
  return request('/simulation/step', { method: 'POST' });
}

// ==================== 仿真结果 ====================

/** 获取仿真结果列表 */
export async function getSimulationResults() {
  return request('/simulation/results');
}

/** 获取指定仿真结果详情 */
export async function getSimulationResult(id: number) {
  return request(`/simulation/results/${id}`);
}

/** 导出 CSV 数据 */
export async function exportCSV(): Promise<string> {
  const res = await fetch(`${BASE}/simulation/export/csv`);
  if (!res.ok) throw new Error('CSV 导出失败');
  return res.text();
}

// ==================== 参数管理 ====================

/** 获取当前参数值 */
export async function getParams(): Promise<SimulationParams> {
  return requestData<SimulationParams>('/params');
}

/** 更新参数值 */
export async function updateParams(params: Partial<SimulationParams>): Promise<SimulationParams> {
  return requestData<SimulationParams>('/params', {
    method: 'PUT',
    body: JSON.stringify(params),
  });
}

/** 设置仿真速度倍率 */
export async function setSimulationSpeed(multiplier: SpeedMultiplier): Promise<void> {
  await requestData<{ speedMultiplier: SpeedMultiplier }>('/simulation/speed', {
    method: 'PUT',
    body: JSON.stringify({ speedMultiplier: multiplier }),
  });
}

/** 获取参数预设方案列表 */
export async function getParameterPresets(): Promise<ParameterPreset[]> {
  return request<ParameterPreset[]>('/params/presets');
}

/** 保存参数预设方案 */
export async function saveParameterPreset(preset: Omit<ParameterPreset, 'id' | 'created_at' | 'updated_at'>) {
  return request('/params/presets', {
    method: 'POST',
    body: JSON.stringify(preset),
  });
}

/** 删除参数预设方案 */
export async function deleteParameterPreset(id: number) {
  return request(`/params/presets/${id}`, { method: 'DELETE' });
}

// ==================== 方案管理 ====================

/** 获取所有方案摘要列表 */
export async function getScenarios(): Promise<ScenarioSummary[]> {
  return request<ScenarioSummary[]>('/scenarios');
}

/** 获取方案完整详情 */
export async function getScenario(id: string): Promise<ScenarioDetailResponse> {
  return request<ScenarioDetailResponse>(`/scenarios/${id}`);
}

/** 保存当前参数+结果为方案 */
export async function saveScenario(name: string, description?: string): Promise<ScenarioSaveResponse> {
  return request<ScenarioSaveResponse>('/scenarios', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  });
}

/** 删除方案 */
export async function deleteScenario(id: string): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/scenarios/${id}`, { method: 'DELETE' });
}

/** 加载方案参数到引擎 */
export async function applyScenario(id: string): Promise<{ config: Record<string, unknown> }> {
  return request<{ config: Record<string, unknown> }>(`/scenarios/${id}/apply`, { method: 'PUT' });
}

// ==================== 事件记录 ====================

/** 获取仿真事件记录 */
export async function getEvents() {
  return request('/events');
}
