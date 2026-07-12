/**
 * NULL轨道交通仿真系统 — 前端类型定义
 * 基于《需求文档》和《详细设计文档》中定义的数据模型
 */

// ==================== 仿真运行状态 ====================

/** 仿真运行状态 */
export type RunState = 'idle' | 'running' | 'paused' | 'stopped';

/** WebSocket 连接状态 */
export type ConnectionState = 'disconnected' | 'connecting' | 'connected';

/** 视图类型 */
export type ViewType = 'overview' | 'power' | 'signal' | 'vehicle' | 'track';

/** 列车工况 */
export type TrainMode = 'traction' | 'coasting' | 'braking' | 'stopped';

/** 车门状态 */
export type DoorStatus = 'open' | 'closed' | 'opening' | 'closing';

/** 速度倍率选项 */
export type SpeedMultiplier = 1 | 5 | 10;

// ==================== 轨道系统 ====================

/** 车站 */
export interface Station {
  id: string;
  name: string;
  chainage: number;          // 车站起点公里标 (m)
  dwell_time: number;        // 默认站停时间 (s)
  platform_half_length: number; // 站台半长 (m), 默认 15
  is_terminus: boolean;      // 是否终点站
  sort_order: number;
}

/** 线路区间段 */
export interface Segment {
  id: string;
  start_chainage: number;
  end_chainage: number;
  gradient: number;          // 坡度 (‰，上坡为正)
  curvature: number;         // 曲率半径 (m，直线为无穷大)
  speed_limit: number;       // 限速 (km/h)
  is_tunnel: boolean;
  sort_order: number;
}

/** 道岔 */
export interface Switch {
  id: string;
  chainage: number;
  type: 'single' | 'crossover';
  normal_direction: string;
  reverse_direction: string;
  lateral_speed_limit: number;
  state: 'normal' | 'reverse' | 'transitioning';
}

/** 轨道电路/计轴器区段 */
export interface TrackCircuit {
  id: string;
  start_chainage: number;
  end_chainage: number;
  direction: 'up' | 'down' | 'both';
  occupied: boolean;
}

/** 轨道状态 */
export interface TrackState {
  occupancy: TrackCircuit[];
  switch_states: Switch[];
}

// ==================== 车辆系统 ====================

/** 车辆参数 */
export interface VehicleParams {
  id: string;
  name: string;
  empty_mass: number;           // 空车质量 (kg)
  passenger_capacity: number;   // 满员载客数
  max_speed: number;            // 最高速度 (km/h)
  max_traction_force: number;   // 最大牵引力 (N)
  max_brake_force: number;      // 最大制动力 (N)
  davis_A: number;              // Davis 公式 A 系数
  davis_B: number;              // Davis 公式 B 系数
  davis_C_front_area: number;   // 迎风面积 (m²)
  davis_C_drag_coeff: number;   // 空气阻力系数
  curve_resist_coeff: number;   // 弯道阻力经验系数 (默认 600)
  tunnel_resist_factor: number; // 隧道阻力加成系数 (默认 1.2)
  regeneration_efficiency: number; // 再生制动效率 (默认 0.3)
  traction_curve: TractionCurvePoint[];
}

/** 牵引特性曲线折点 */
export interface TractionCurvePoint {
  speed: number;           // 速度 (km/h)
  force_percent: number;   // 最大牵引力百分比 [0, 1]
  sort_order: number;
}

/** 列车实时状态 */
export interface TrainState {
  id: string;
  position: number;           // 当前公里标 (m)
  speed: number;              // 当前速度 (km/h)
  acceleration: number;       // 当前加速度 (m/s²)
  jerk: number;               // 加加速度 / 冲击率 (m/s³)
  mode: TrainMode;            // 工况: traction / coasting / braking
  mass: number;               // 当前总质量 (kg)
  passenger_count: number;    // 当前载客数
  door_status: DoorStatus;
  pantograph_voltage: number; // 受电弓端电压 (V)
  power_demand: number;       // 功率请求 (kW)
  distance_to_station: number; // 距目标站距离 (m)
  target_station_id: string;   // 目标站 ID
  fault_alarm: FaultAlarm | null;
}

/** 故障告警 */
export interface FaultAlarm {
  code: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
}

/** 控制指令 */
export interface ControlCommands {
  traction_level: number;     // 牵引级位 [0, 1]
  brake_level: number;        // 制动级位 [0, 1]
  emergency_brake: boolean;
}

// ==================== 供电系统 ====================

/** 变电所 */
export interface Substation {
  id: string;
  name: string;
  chainage: number;
  rated_voltage: number;      // 额定电压 (V)，默认 1500
  rated_power: number;        // 额定容量 (kW)
  output_current: number;     // 当前输出电流 (A)
  output_power: number;       // 当前输出功率 (kW)
}

/** 电压分布点 */
export interface VoltagePoint {
  chainage: number;
  voltage: number;
}

/** 供电状态 */
export interface PowerState {
  substations: Substation[];
  voltage_profile: VoltagePoint[];
  total_consumption: number;     // 总牵引能耗 (kWh)
  total_regeneration: number;    // 总再生电量 (kWh)
  regeneration_rate: number;     // 再生制动能量利用率
}

// ==================== 信号系统 ====================

/** 信号控制指令 */
export interface SignalCommand {
  train_id: string;
  traction_level: number;
  brake_level: number;
  emergency_brake?: boolean;
  running_phase?: string;
}

/** 紧急制动指令 */
export interface EmergencyBrakeCommand {
  train_id: string;
  reason: string;
}

/** ATP 移动授权包络（后端 maProfile） */
export interface MaProfileEntry {
  train_id: string;
  ma_end_chainage: number;
  safety_distance: number;
}

/** 区段限速与 ATP 限速（后端 speedLimits） */
export interface SpeedLimitEntry {
  train_id: string;
  permanent_limit: number;
  atp_limit: number;
}

/** ATS 时刻表偏差（后端 timetableDeviation） */
export interface TimetableDeviationEntry {
  train_id: string;
  station_id: string;
  delay_arrival: number;
  nominal_dwell: number;
  adjusted_dwell: number;
}

/** 信号状态 */
export interface SignalState {
  commands: SignalCommand[];
  emergency_brake: EmergencyBrakeCommand[];
  train_intervals: number[];   // 各列车发车间隔 (s)
  ma_profiles: MaProfileEntry[];
  speed_limits: SpeedLimitEntry[];
  timetable_deviations: TimetableDeviationEntry[];
}

export const EMPTY_SIGNAL_STATE: SignalState = {
  commands: [],
  emergency_brake: [],
  train_intervals: [],
  ma_profiles: [],
  speed_limits: [],
  timetable_deviations: [],
};

// ==================== 仿真数据快照 ====================

/** 仿真时钟 */
export interface SimulationClock {
  elapsed: number;             // 已仿真时间 (s)
  speed_multiplier: SpeedMultiplier;
}

/** 仿真快照 — WebSocket 每步推送的数据 */
export interface SimulationSnapshot {
  clock: SimulationClock;
  trains: TrainState[];
  power: PowerState;
  signaling: SignalState;
  track: TrackState;
  events: SimulationEvent[];
}

/** 仿真事件 */
export interface SimulationEvent {
  time: number;
  type: 'info' | 'warning' | 'error' | 'overspeed' | 'emergency_brake' | 'door_fault' | 'power_trip';
  message: string;
  train_id?: string;
}

// ==================== 仿真参数配置 ====================

/** 仿真参数（供参数面板编辑使用） */
export interface SimulationParams {
  vehicle: Partial<VehicleParams>;
  track: {
    segment_id?: string;
    gradient?: number;
    curvature?: number;
    speed_limit?: number;
  };
  power: {
    pantograph_voltage?: number;
    substation_capacity?: number;
  };
  signal: {
    dwell_time?: number;
    departure_interval?: number;
    target_speed_ratio?: number;
  };
}

/** 仿真配置 */
export interface SimulationConfig {
  time_step: number;              // 仿真步长 (s)，默认 0.1
  total_time: number;             // 总仿真时长 (s)，默认 600
  speed_multiplier: SpeedMultiplier;
  pantograph_voltage: number;     // 固定网压 (V)
  signal_mode: 'three_stage' | 'atp_ato';
  target_speed_ratio: number;     // 目标速度 = 限速 × 此比例
  station_stop_tolerance: number; // 站台停车容忍度 (m)
  train_count: number;
  departure_interval: number;     // 发车间隔 (s)
}

/** 参数预设方案 */
export interface ParameterPreset {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

// ==================== 统计摘要 ====================

/** 仿真运行统计 */
export interface SimulationStats {
  total_distance: number;       // 总运行距离 (m)
  avg_speed: number;            // 平均速度 (km/h)
  max_speed: number;            // 最高速度 (km/h)
  total_energy_consumption: number; // 总牵引能耗 (kWh)
  total_regeneration: number;   // 总再生电量 (kWh)
  trip_time: number;            // 运行时间 (s)
  stop_count: number;           // 站停次数
}

// ==================== 图表历史缓冲 ====================

/** 实时曲线历史数据（前端累积，供 ECharts 绘制） */
export interface ChartHistory {
  speedTime: [number, number][];       // [时间s, 速度km/h]
  accelTime: [number, number][];       // [时间s, 加速度m/s²]
  jerkTime: [number, number][];        // [时间s, 冲击率m/s³]
  speedPosition: [number, number][];   // [位置m, 速度km/h]
  positionTime: [number, number][];    // [时间s, 位置m] — UI-SIG-03 运行图
}

// ==================== Mock 回放数据 ====================

/** 预录回放单帧（紧凑格式，比完整 SimulationSnapshot 小） */
export interface MockReplayFrame {
  t: number;                // 仿真时间 (s)
  position: number;         // 公里标 (m)
  speed: number;            // 速度 (km/h)
  acceleration: number;     // 加速度 (m/s²)
  jerk?: number;            // 冲击率 (m/s³)
  mode: TrainMode;
  mass: number;
  passenger_count: number;
  pantograph_voltage: number;
  power_demand: number;
  running_phase?: string;
  distance_to_station?: number;
  target_station_id?: string;
  traction_level?: number;
  brake_level?: number;
}

/** 预录回放场景 */
export interface MockReplayScenario {
  meta: {
    name: string;
    description: string;
    timeStep: number;       // 帧间隔 (s)，默认 1.0
    totalDuration: number;  // 总时长 (s)
  };
  vehicleParams: VehicleParams;
  frames: MockReplayFrame[];
}

/** Mock 轨迹生成器输入（车辆 + 线路 + 信号参数快照） */
export interface MockSimInput {
  vehicle: VehicleParams;
  track: {
    gradient: number;      // ‰，上坡为正；覆盖 B→C 段
    curvature: number;     // m，MVP 弯道阻力简化为 0
    speed_limit: number;   // km/h
  };
  signal: {
    dwell_time: number;
    target_speed_ratio: number;
  };
  passenger_load_ratio: number;   // 0~1，默认 0.6 (AW2)
}

// ==================== 全局应用状态 ====================

/** 全局仿真应用状态 */
export interface AppState {
  /** WebSocket 连接状态 */
  connection: ConnectionState;
  /** 仿真运行状态 */
  runState: RunState;
  /** 当前选中的视图 */
  activeView: ViewType;
  /** 仿真时钟 */
  clock: SimulationClock;
  /** 列车状态列表 */
  trains: TrainState[];
  /** 供电状态 */
  power: PowerState;
  /** 信号状态 */
  signaling: SignalState;
  /** 轨道状态 */
  track: TrackState;
  /** 参数配置 */
  params: SimulationParams;
  /** 统计数据 */
  stats: SimulationStats;
  /** 仿真事件 */
  events: SimulationEvent[];
  /** 渲染帧率 */
  fps: number;
  /** 曲线历史缓冲 */
  chartHistory: ChartHistory;
  /** 线路布局数据（Mock 模式或从后端初始化） */
  lineLayout: LineLayout | null;
  /** 线路剖面分段（坡度/限速，供纵断面图） */
  profileSegments: import('../data/mvpLineLayout').ProfileSegment[] | null;
  /** 车辆参数步进基准值（首次从后端/默认值锁定，步进=基准×10%） */
  vehicleParamBaselines: import('../utils/paramStep').VehicleParamBaselines;
  /** 线路参数步进基准值 */
  trackParamBaselines: import('../utils/paramStep').TrackParamBaselines;
  /** 信号参数步进基准值 */
  signalParamBaselines: import('../utils/paramStep').SignalParamBaselines;
  /** 牵引特性曲线各折点步进基准值 */
  tractionCurveBaselines: import('../utils/paramStep').TractionCurvePointBaseline[];
}

// ==================== API 原始类型（camelCase，适配前） ====================

/** 后端 WS 推送的 camelCase 列车状态 */
export interface ApiTrainState {
  id: string;
  position: number;
  speed: number;
  acceleration: number;
  jerk?: number;
  mode: TrainMode;
  mass: number;
  passengerCount: number;
  pantographVoltage: number;
  powerDemand: number;
  doorStatus: DoorStatus;
  distanceToStation: number;
  targetStationId: string;
  faultAlarm: FaultAlarm | null;
}

export interface ApiControlCommand {
  trainId: string;
  tractionLevel: number;
  brakeLevel: number;
  emergencyBrake?: boolean;
  runningPhase?: string;
}

export interface ApiSubstation {
  id: string;
  name: string;
  chainage: number;
  ratedVoltage: number;
  ratedPower: number;
  outputCurrent: number;
  outputPower: number;
}

export interface ApiVoltagePoint {
  chainage: number;
  voltage: number;
}

export interface ApiSimulationSnapshot {
  clock: { elapsed: number; speedMultiplier: SpeedMultiplier };
  trains: ApiTrainState[];
  power: {
    substations: ApiSubstation[];
    voltageProfile: ApiVoltagePoint[];
    totalConsumption: number;
    totalRegeneration: number;
  };
  signaling: {
    controlCommands?: ApiControlCommand[];
    commands?: unknown[];
    emergencyBrakes: unknown[];
    maProfile?: Array<{
      trainId: string;
      maEndChainage: number;
      safetyDistance: number;
    }>;
    speedLimits?: Array<{
      trainId: string;
      permanentLimit: number;
      atpLimit: number;
    }>;
    timetableDeviation?: Array<{
      trainId: string;
      stationId: string;
      delayArrival: number;
      nominalDwell: number;
      adjustedDwell: number;
    }>;
  };
  track: { occupancy: unknown[]; switchStates: unknown[] };
  events: SimulationEvent[];
}

// ==================== WebSocket 消息类型 ====================

/** 服务端推送消息 */
export type ServerMessage =
  | { type: 'simulation_snapshot'; timestamp: number; data: ApiSimulationSnapshot }
  | { type: 'init_state'; config: Record<string, unknown>; state?: { runState: RunState; simulationTime: number } }
  | { type: 'simulation_status'; data: { runState: RunState; simulationTime: number; reason?: string } }
  | { type: 'simulation_complete'; data: Record<string, unknown> }
  | { type: 'heartbeat'; serverTime?: string };

/** 客户端发送消息 */
export type ClientMessage =
  | { type: 'sim_control'; action: 'start' | 'pause' | 'resume' | 'stop' | 'step' }
  | { type: 'param_update'; params: Partial<SimulationParams> }
  | { type: 'manual_control'; emergencyBrake: boolean };

/** 初始化配置 */
export interface InitConfig {
  line: {
    name: string;
    stations: Station[];
    segments: Segment[];
  };
  vehicles: {
    params: VehicleParams;
  };
  simulation: SimulationConfig;
}

// ==================== 线路布局（交互式线路图） ====================

/** 站内股道布局 */
export interface TrackLayout {
  track_id: string;
  name: string;           // "正线", "侧线1", "存车线"
  type: 'main' | 'siding' | 'parking';
  occupied: boolean;
}

/** 车站布局（扩展现有 Station） */
export interface StationLayout extends Station {
  length: number;         // 站长 (m)
  tracks: TrackLayout[];
  arrival_time?: number;  // 到达仿真时间 (s)
  departure_time?: number;
  dwell_time_actual?: number; // 实际停站时长 (s)
  occupancy_rate: number; // 站台占用率 [0, 1]
}

/** 区间轨道段（两站之间） */
export interface InterStationSegment {
  start_chainage: number;
  end_chainage: number;
  circuits: TrackCircuit[];
}

/** 完整线路布局数据 */
export interface LineLayout {
  name: string;
  stations: StationLayout[];
  segments: InterStationSegment[];
  total_length: number;
}
