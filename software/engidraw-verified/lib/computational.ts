import type { ValidationCheck, ValidationReport, StandardProfile, UnitSystem } from './engidraw';

export interface GyroidSpec {
  modelType: 'gyroid-thermal-core';
  name: string;
  drawingNumber: string;
  revision: string;
  units: UnitSystem;
  standard: StandardProfile;
  width: number;
  depth: number;
  height: number;
  cellSize: number;
  wallThickness: number;
  resolution: number;
  material: string;
  process: string;
}

export interface Vec3 { x: number; y: number; z: number }
export interface Triangle { a: Vec3; b: Vec3; c: Vec3; normal: Vec3 }

export interface MeshStats {
  triangleCount: number;
  estimatedSolidVolume: number;
  surfaceArea: number;
  gridSpacing: number;
  bounds: { width: number; depth: number; height: number };
}

export interface ComputationalArtifact {
  mesh: Triangle[];
  stl: string;
  recipe: {
    schemaVersion: 'engidraw.cem-recipe.v1';
    kernel: 'implicit-sdf-marching-tetrahedra';
    specification: GyroidSpec;
    validation: ValidationReport;
    modelHash: string;
    meshHash: string;
    stats: MeshStats;
    releaseState: 'RESEARCH_GEOMETRY_NOT_PHYSICS_VALIDATED';
    requiredNextGates: string[];
  };
  stlFilename: string;
  recipeFilename: string;
}

export const DEFAULT_GYROID_SPEC: GyroidSpec = {
  modelType: 'gyroid-thermal-core',
  name: 'GYROID THERMAL CORE',
  drawingNumber: 'ED-CEM-001',
  revision: 'A',
  units: 'mm',
  standard: 'ISO-128-2022',
  width: 60,
  depth: 60,
  height: 40,
  cellSize: 15,
  wallThickness: 3,
  resolution: 20,
  material: 'AlSi10Mg',
  process: 'LASER POWDER BED FUSION',
};

export function validateGyroidSpecification(spec: GyroidSpec): ValidationReport {
  const checks: ValidationCheck[] = [];
  const add = (id: string, label: string, condition: boolean, ok: string, bad: string) => checks.push({ id, label, status: condition ? 'pass' : 'fail', detail: condition ? ok : bad } as ValidationCheck);
  const dimensions = [spec.width, spec.depth, spec.height, spec.cellSize, spec.wallThickness];
  add('cem.numeric', 'Geometry inputs are finite and positive', dimensions.every((value) => Number.isFinite(value) && value > 0), 'All physical dimensions are positive.', 'Width, depth, height, cell size, and wall thickness must be positive numbers.');
  add('cem.resolution', 'Meshing resolution is supported', Number.isInteger(spec.resolution) && spec.resolution >= 16 && spec.resolution <= 40, `${spec.resolution} cells on the longest axis.`, 'The browser MVP supports an integer resolution from 16 through 40.');
  add('cem.cell-fit', 'Periodic cells fit the design envelope', spec.cellSize <= Math.min(spec.width, spec.depth, spec.height), 'At least one complete cell fits every axis.', 'Cell size must not exceed the smallest envelope dimension.');
  add('cem.wall-cell', 'Wall-to-cell relationship is valid', spec.wallThickness < spec.cellSize * 0.45, `Wall thickness is ${round(spec.wallThickness / spec.cellSize * 100)}% of cell size.`, 'Wall thickness must be less than 45% of cell size for this model.');
  const gridSpacing = Math.max(spec.width, spec.depth, spec.height) / spec.resolution;
  add('cem.discretization', 'Grid resolves the requested wall', gridSpacing <= spec.wallThickness, `Grid spacing ${round(gridSpacing)} ${spec.units}.`, `Grid spacing ${round(gridSpacing)} ${spec.units} exceeds wall thickness; raise resolution or increase thickness.`);
  add('cem.metadata', 'Manufacturing context declared', Boolean(spec.material.trim() && spec.process.trim()), `${spec.material} · ${spec.process}`, 'Material and manufacturing process are required.');
  checks.push({
    id: 'cem.physics',
    label: 'Physics validation required',
    status: 'warning',
    detail: 'Geometry generation does not prove thermal, flow, fatigue, pressure, or manufacturability performance.',
  });
  const passCount = checks.filter((check) => check.status === 'pass').length;
  const failCount = checks.filter((check) => check.status === 'fail').length;
  const warningCount = checks.filter((check) => check.status === 'warning').length;
  return { status: failCount ? 'rejected' : 'validated', checks, passCount, failCount, warningCount };
}

export async function buildGyroidArtifact(specInput: GyroidSpec): Promise<ComputationalArtifact> {
  const spec = JSON.parse(JSON.stringify(specInput)) as GyroidSpec;
  const validation = validateGyroidSpecification(spec);
  if (validation.status === 'rejected') {
    const reasons = validation.checks.filter((check) => check.status === 'fail').map((check) => check.detail).join(' ');
    throw new Error(`Computational geometry rejected: ${reasons}`);
  }
  const { triangles, occupiedCells, totalCells, gridSpacing } = buildGyroidMesh(spec);
  const stl = meshToAsciiStl(triangles, safeName(spec.drawingNumber));
  const modelHash = await sha256(canonicalJson(spec));
  const meshHash = await sha256(stl);
  const stats: MeshStats = {
    triangleCount: triangles.length,
    estimatedSolidVolume: occupiedCells / totalCells * (spec.width * spec.depth * spec.height),
    surfaceArea: triangles.reduce((sum, triangle) => sum + triangleArea(triangle), 0),
    gridSpacing,
    bounds: { width: spec.width, depth: spec.depth, height: spec.height },
  };
  const base = `${safeName(spec.drawingNumber)}_REV-${safeName(spec.revision)}`;
  return {
    mesh: triangles,
    stl,
    recipe: {
      schemaVersion: 'engidraw.cem-recipe.v1',
      kernel: 'implicit-sdf-marching-tetrahedra',
      specification: spec,
      validation,
      modelHash,
      meshHash,
      stats,
      releaseState: 'RESEARCH_GEOMETRY_NOT_PHYSICS_VALIDATED',
      requiredNextGates: [
        'Mesh repair and watertightness verification in the production geometry kernel',
        'Thermal and conjugate heat-transfer analysis',
        'Pressure-drop and structural analysis',
        'Process-specific minimum-feature and overhang validation',
        'Coupon printing, CT inspection, and physical performance testing',
        'Qualified engineer approval',
      ],
    },
    stlFilename: `${base}.stl`,
    recipeFilename: `${base}.cem-recipe.json`,
  };
}

function buildGyroidMesh(spec: GyroidSpec): { triangles: Triangle[]; occupiedCells: number; totalCells: number; gridSpacing: number } {
  const { nx, ny, nz } = gridCounts(spec);
  const dx = spec.width / nx;
  const dy = spec.depth / ny;
  const dz = spec.height / nz;
  const values = new Float32Array((nx + 1) * (ny + 1) * (nz + 1));
  const index = (i: number, j: number, k: number) => (k * (ny + 1) + j) * (nx + 1) + i;
  const field = (x: number, y: number, z: number) => gyroidField(x, y, z, spec);
  for (let k = 0; k <= nz; k += 1) {
    for (let j = 0; j <= ny; j += 1) {
      for (let i = 0; i <= nx; i += 1) {
        values[index(i, j, k)] = field(-spec.width / 2 + i * dx, -spec.depth / 2 + j * dy, -spec.height / 2 + k * dz);
      }
    }
  }

  const cubeCorners = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]] as const;
  const tetrahedra = [[0, 5, 1, 6], [0, 1, 2, 6], [0, 2, 3, 6], [0, 3, 7, 6], [0, 7, 4, 6], [0, 4, 5, 6]] as const;
  const triangles: Triangle[] = [];
  let occupiedCells = 0;
  for (let k = 0; k < nz; k += 1) {
    for (let j = 0; j < ny; j += 1) {
      for (let i = 0; i < nx; i += 1) {
        const points = cubeCorners.map(([ox, oy, oz]) => ({ x: -spec.width / 2 + (i + ox) * dx, y: -spec.depth / 2 + (j + oy) * dy, z: -spec.height / 2 + (k + oz) * dz }));
        const scalar = cubeCorners.map(([ox, oy, oz]) => values[index(i + ox, j + oy, k + oz)]);
        if (scalar.some((value) => value <= 0)) occupiedCells += 1;
        tetrahedra.forEach((tetra) => polygonizeTetra(tetra.map((corner) => points[corner]), tetra.map((corner) => scalar[corner]), field, triangles));
      }
    }
  }
  return { triangles, occupiedCells, totalCells: nx * ny * nz, gridSpacing: Math.max(dx, dy, dz) };
}

function gridCounts(spec: GyroidSpec) {
  const longest = Math.max(spec.width, spec.depth, spec.height);
  return {
    nx: Math.max(4, Math.round(spec.resolution * spec.width / longest)),
    ny: Math.max(4, Math.round(spec.resolution * spec.depth / longest)),
    nz: Math.max(4, Math.round(spec.resolution * spec.height / longest)),
  };
}

function gyroidField(x: number, y: number, z: number, spec: GyroidSpec): number {
  const frequency = (Math.PI * 2) / spec.cellSize;
  const gx = x * frequency;
  const gy = y * frequency;
  const gz = z * frequency;
  const gyroid = Math.sin(gx) * Math.cos(gy) + Math.sin(gy) * Math.cos(gz) + Math.sin(gz) * Math.cos(gx);
  const sheetLevel = Math.min(1.15, Math.max(0.06, spec.wallThickness * frequency * 0.34));
  const gyroidSheet = Math.abs(gyroid) - sheetLevel;
  const edgeDistance = Math.max(Math.abs(x) - spec.width / 2, Math.abs(y) - spec.depth / 2, Math.abs(z) - spec.height / 2);
  return Math.max(gyroidSheet, edgeDistance * frequency);
}

function polygonizeTetra(points: Vec3[], values: number[], field: (x: number, y: number, z: number) => number, output: Triangle[]) {
  const edges = [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]] as const;
  const intersections: Vec3[] = [];
  edges.forEach(([a, b]) => {
    if ((values[a] <= 0) === (values[b] <= 0)) return;
    const denominator = values[a] - values[b];
    const t = denominator === 0 ? 0.5 : values[a] / denominator;
    intersections.push({
      x: points[a].x + (points[b].x - points[a].x) * t,
      y: points[a].y + (points[b].y - points[a].y) * t,
      z: points[a].z + (points[b].z - points[a].z) * t,
    });
  });
  if (intersections.length === 3) output.push(orientedTriangle(intersections[0], intersections[1], intersections[2], field));
  if (intersections.length === 4) {
    output.push(orientedTriangle(intersections[0], intersections[1], intersections[2], field));
    output.push(orientedTriangle(intersections[0], intersections[2], intersections[3], field));
  }
}

function orientedTriangle(a: Vec3, b: Vec3, c: Vec3, field: (x: number, y: number, z: number) => number): Triangle {
  let normal = normalize(cross(subtract(b, a), subtract(c, a)));
  const center = { x: (a.x + b.x + c.x) / 3, y: (a.y + b.y + c.y) / 3, z: (a.z + b.z + c.z) / 3 };
  const epsilon = 0.02;
  const gradient = normalize({
    x: field(center.x + epsilon, center.y, center.z) - field(center.x - epsilon, center.y, center.z),
    y: field(center.x, center.y + epsilon, center.z) - field(center.x, center.y - epsilon, center.z),
    z: field(center.x, center.y, center.z + epsilon) - field(center.x, center.y, center.z - epsilon),
  });
  if (dot(normal, gradient) < 0) { const swap = b; b = c; c = swap; normal = multiply(normal, -1); }
  return { a, b, c, normal };
}

export function drawMesh(canvas: HTMLCanvasElement, triangles: Triangle[], rotationX = -0.55, rotationY = 0.72) {
  const context = canvas.getContext('2d');
  if (!context) return;
  const ratio = Math.min(globalThis.devicePixelRatio || 1, 2);
  const cssWidth = Math.max(canvas.clientWidth, 320);
  const cssHeight = Math.max(canvas.clientHeight, 300);
  canvas.width = cssWidth * ratio;
  canvas.height = cssHeight * ratio;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, cssWidth, cssHeight);
  context.fillStyle = '#f9fbfa';
  context.fillRect(0, 0, cssWidth, cssHeight);
  if (!triangles.length) return;

  const previewStride = Math.max(1, Math.ceil(triangles.length / 50000));
  const previewTriangles = previewStride === 1 ? triangles : triangles.filter((_, index) => index % previewStride === 0);
  const transformed = previewTriangles.map((triangle) => {
    const points = [triangle.a, triangle.b, triangle.c].map((point) => rotate(point, rotationX, rotationY));
    const normal = rotate(triangle.normal, rotationX, rotationY);
    return { points, normal, z: points.reduce((sum, point) => sum + point.z, 0) / 3 };
  }).sort((a, b) => a.z - b.z);
  const all = transformed.flatMap((triangle) => triangle.points);
  const maxRange = Math.max(Math.max(...all.map((point) => point.x)) - Math.min(...all.map((point) => point.x)), Math.max(...all.map((point) => point.y)) - Math.min(...all.map((point) => point.y)));
  const scale = Math.min(cssWidth, cssHeight) * 0.72 / Math.max(maxRange, 1);
  const light = normalize({ x: -0.4, y: -0.55, z: 0.8 });
  transformed.forEach(({ points, normal }) => {
    const shade = Math.max(0, dot(normal, light));
    const tone = Math.round(53 + shade * 72);
    context.beginPath();
    points.forEach((point, index) => {
      const px = cssWidth / 2 + point.x * scale;
      const py = cssHeight / 2 - point.y * scale;
      if (index === 0) context.moveTo(px, py); else context.lineTo(px, py);
    });
    context.closePath();
    context.fillStyle = `rgb(${tone - 8},${tone + 30},${tone + 17})`;
    context.fill();
  });
}

function meshToAsciiStl(triangles: Triangle[], name: string): string {
  const lines = [`solid ${name}`];
  triangles.forEach((triangle) => {
    lines.push(`  facet normal ${coord(triangle.normal.x)} ${coord(triangle.normal.y)} ${coord(triangle.normal.z)}`);
    lines.push('    outer loop');
    [triangle.a, triangle.b, triangle.c].forEach((point) => lines.push(`      vertex ${coord(point.x)} ${coord(point.y)} ${coord(point.z)}`));
    lines.push('    endloop', '  endfacet');
  });
  lines.push(`endsolid ${name}`);
  return lines.join('\n');
}

function triangleArea(triangle: Triangle): number {
  const vector = cross(subtract(triangle.b, triangle.a), subtract(triangle.c, triangle.a));
  return 0.5 * Math.hypot(vector.x, vector.y, vector.z);
}

function subtract(a: Vec3, b: Vec3): Vec3 { return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z }; }
function multiply(a: Vec3, scalar: number): Vec3 { return { x: a.x * scalar, y: a.y * scalar, z: a.z * scalar }; }
function cross(a: Vec3, b: Vec3): Vec3 { return { x: a.y * b.z - a.z * b.y, y: a.z * b.x - a.x * b.z, z: a.x * b.y - a.y * b.x }; }
function dot(a: Vec3, b: Vec3): number { return a.x * b.x + a.y * b.y + a.z * b.z; }
function normalize(a: Vec3): Vec3 { const length = Math.hypot(a.x, a.y, a.z) || 1; return { x: a.x / length, y: a.y / length, z: a.z / length }; }
function rotate(point: Vec3, rx: number, ry: number): Vec3 {
  const x1 = point.x * Math.cos(ry) + point.z * Math.sin(ry);
  const z1 = -point.x * Math.sin(ry) + point.z * Math.cos(ry);
  return { x: x1, y: point.y * Math.cos(rx) - z1 * Math.sin(rx), z: point.y * Math.sin(rx) + z1 * Math.cos(rx) };
}
function coord(value: number): string { return (Math.round(value * 100000) / 100000).toFixed(5); }
function round(value: number): string { return (Math.round(value * 100) / 100).toFixed(2); }
function safeName(value: string): string { return value.trim().replace(/[^a-z0-9._-]+/gi, '-').replace(/^-+|-+$/g, '') || 'MODEL'; }
function canonicalJson(value: unknown): string { return JSON.stringify(sort(value)); }
function sort(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sort);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, sort(item)]));
  return value;
}
async function sha256(value: string): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('');
}
