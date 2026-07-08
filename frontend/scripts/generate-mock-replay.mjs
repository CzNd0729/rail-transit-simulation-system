/**
 * 生成 A→B→C 三站运行的预录时序数据（离线 fixture）
 *
 * 注意：运行时不再读取此 JSON。前端 Mock 模式在每次「运行」时
 * 由 src/mock/generateMockTrajectory.ts 按当前参数动态生成轨迹。
 * 本脚本仅用于导出回归测试金标准。
 *
 * Run: node scripts/generate-mock-replay.mjs
 */
import { writeFileSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, '../src/data/mockReplay/scenario-default.json');

const STATIONS = [0, 1500, 3200];
const DWELL = 30;
const DT = 1.0;

function segmentProfile(from, to, startT, mode) {
  const frames = [];
  const dist = to - from;
  const duration = dist / 20;
  const steps = Math.ceil(duration / DT);
  for (let i = 0; i <= steps; i++) {
    const ratio = i / steps;
    const pos = from + dist * ratio;
    let speed, accel, trainMode;
    if (mode === 'run') {
      if (ratio < 0.3)       { speed = 64 * (ratio / 0.3); accel = 0.8; trainMode = 'traction'; }
      else if (ratio < 0.7)  { speed = 64; accel = 0; trainMode = 'coasting'; }
      else                   { speed = 64 * (1 - (ratio - 0.7) / 0.3); accel = -0.9; trainMode = 'braking'; }
    } else {
      speed = 0; accel = 0; trainMode = 'coasting';
    }
    frames.push({
      t: startT + i * DT,
      position: Math.round(pos * 10) / 10,
      speed: Math.round(speed * 10) / 10,
      acceleration: Math.round(accel * 100) / 100,
      mode: trainMode,
      mass: 215000,
      passenger_count: 900,
      pantograph_voltage: 1500,
      power_demand: trainMode === 'traction' ? 3200 : 0,
    });
  }
  return frames;
}

let frames = [];
let t = 0;

frames.push(...segmentProfile(STATIONS[0], STATIONS[1], t, 'run'));
t = frames[frames.length - 1].t + DWELL;
for (let i = 0; i < DWELL; i++) {
  frames.push({ t: t + i, position: STATIONS[1], speed: 0, acceleration: 0,
    mode: 'coasting', mass: 215000, passenger_count: 900, pantograph_voltage: 1500, power_demand: 0 });
}
t += DWELL;

const bToC = segmentProfile(STATIONS[1], STATIONS[2], t, 'run');
bToC.forEach((f, i) => {
  if (f.mode === 'traction' && i > 0) f.acceleration = 0.5;
});
frames.push(...bToC);
t = frames[frames.length - 1].t + DWELL;
for (let i = 0; i < DWELL; i++) {
  frames.push({ t: t + i, position: STATIONS[2], speed: 0, acceleration: 0,
    mode: 'coasting', mass: 215000, passenger_count: 900, pantograph_voltage: 1500, power_demand: 0 });
}

const scenario = {
  meta: {
    name: 'A站→B站→C站 标准运行',
    description: '迭代一验收场景1：三段式牵引-惰行-制动，B→C含上坡段',
    timeStep: DT,
    totalDuration: frames[frames.length - 1].t,
  },
  vehicleParams: {
    id: 'TYPE_A', name: 'A型车', empty_mass: 200000, passenger_capacity: 1500,
    max_speed: 80, max_traction_force: 400000, max_brake_force: 350000,
    davis_A: 0.01, davis_B: 0.0001, davis_C_front_area: 10, davis_C_drag_coeff: 0.5,
    curve_resist_coeff: 600, tunnel_resist_factor: 1.2, regeneration_efficiency: 0.3,
    traction_curve: [
      { speed: 0, force_percent: 1.0, sort_order: 0 },
      { speed: 40, force_percent: 1.0, sort_order: 1 },
      { speed: 80, force_percent: 0.5, sort_order: 2 },
    ],
  },
  frames,
};

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify(scenario, null, 2));
console.log(`Generated ${frames.length} frames, duration ${scenario.meta.totalDuration}s → ${OUT}`);
