export const GENERATOR_VERSION = '0.1.0';

export type PartType = 'plate' | 'flange' | 'shaft';
export type UnitSystem = 'mm' | 'in';
export type StandardProfile = 'ASME-Y14.5-2018-R2024' | 'ISO-128-2022';

interface BaseSpec {
  partType: PartType;
  name: string;
  drawingNumber: string;
  revision: string;
  units: UnitSystem;
  standard: StandardProfile;
  material: string;
}

export interface PlateSpec extends BaseSpec {
  partType: 'plate';
  width: number;
  height: number;
  thickness: number;
  cornerRadius: number;
  holeDiameter: number;
  edgeX: number;
  edgeY: number;
}

export interface FlangeSpec extends BaseSpec {
  partType: 'flange';
  outerDiameter: number;
  boreDiameter: number;
  thickness: number;
  boltCircleDiameter: number;
  boltHoleDiameter: number;
  boltCount: number;
}

export interface ShaftSegment {
  length: number;
  diameter: number;
}

export interface ShaftSpec extends BaseSpec {
  partType: 'shaft';
  segments: [ShaftSegment, ShaftSegment, ShaftSegment];
}

export type EngineeringSpec = PlateSpec | FlangeSpec | ShaftSpec;

export interface ValidationCheck {
  id: string;
  label: string;
  status: 'pass' | 'fail' | 'warning';
  detail: string;
}

export interface ValidationReport {
  status: 'validated' | 'rejected';
  checks: ValidationCheck[];
  passCount: number;
  failCount: number;
  warningCount: number;
}

export interface ArtifactManifest {
  schemaVersion: 'engidraw.manifest.v1';
  generator: { name: 'EngiDraw Verified'; version: string };
  drawingNumber: string;
  revision: string;
  partType: PartType;
  standardProfile: StandardProfile;
  units: UnitSystem;
  specHash: string;
  artifactHash: string;
  deterministic: true;
  validation: ValidationReport;
  specification: EngineeringSpec;
  releaseState: 'VALIDATED_NOT_ENGINEER_APPROVED';
  disclaimer: string;
}

export interface GeneratedArtifact {
  svg: string;
  manifest: ArtifactManifest;
  svgFilename: string;
  manifestFilename: string;
}

export interface InterpretationResult {
  specification: EngineeringSpec | null;
  matchedFields: string[];
  errors: string[];
}

const BASE = {
  revision: 'A',
  units: 'mm' as UnitSystem,
  standard: 'ASME-Y14.5-2018-R2024' as StandardProfile,
  material: '6061-T6 ALUMINUM',
};

export const DEFAULT_SPECS: Record<PartType, EngineeringSpec> = {
  plate: {
    ...BASE,
    partType: 'plate',
    name: 'MOUNTING PLATE',
    drawingNumber: 'ED-PL-001',
    width: 120,
    height: 80,
    thickness: 10,
    cornerRadius: 5,
    holeDiameter: 8,
    edgeX: 15,
    edgeY: 15,
  },
  flange: {
    ...BASE,
    partType: 'flange',
    name: 'BOLT FLANGE',
    drawingNumber: 'ED-FL-001',
    material: 'AISI 1045 STEEL',
    outerDiameter: 160,
    boreDiameter: 60,
    thickness: 18,
    boltCircleDiameter: 120,
    boltHoleDiameter: 12,
    boltCount: 8,
  },
  shaft: {
    ...BASE,
    partType: 'shaft',
    name: 'STEPPED SHAFT',
    drawingNumber: 'ED-SH-001',
    material: 'AISI 4140 STEEL',
    segments: [
      { length: 30, diameter: 30 },
      { length: 80, diameter: 45 },
      { length: 30, diameter: 30 },
    ],
  },
};

export function cloneSpec<T extends EngineeringSpec>(spec: T): T {
  return JSON.parse(JSON.stringify(spec)) as T;
}

function finitePositive(value: number): boolean {
  return Number.isFinite(value) && value > 0;
}

function finiteNonNegative(value: number): boolean {
  return Number.isFinite(value) && value >= 0;
}

export function validateSpecification(spec: EngineeringSpec): ValidationReport {
  const checks: ValidationCheck[] = [];
  const add = (id: string, label: string, passes: boolean, passDetail: string, failDetail: string) => {
    checks.push({ id, label, status: passes ? 'pass' : 'fail', detail: passes ? passDetail : failDetail });
  };

  add('metadata.name', 'Part name present', spec.name.trim().length > 0, spec.name.trim(), 'Enter a part name.');
  add('metadata.number', 'Drawing number present', spec.drawingNumber.trim().length > 0, spec.drawingNumber.trim(), 'Enter a drawing number.');
  add('metadata.revision', 'Revision present', spec.revision.trim().length > 0, `Revision ${spec.revision.trim()}`, 'Enter a revision.');
  add('metadata.material', 'Material declared', spec.material.trim().length > 0, spec.material.trim(), 'Declare a material or use UNSPECIFIED.');
  add('profile.standard', 'Standards profile selected', Boolean(spec.standard), spec.standard, 'Select a standards profile.');
  add('profile.units', 'Unit system selected', spec.units === 'mm' || spec.units === 'in', spec.units, 'Use mm or in.');

  if (spec.partType === 'plate') {
    const dimensionsValid = [spec.width, spec.height, spec.thickness, spec.holeDiameter].every(finitePositive)
      && [spec.cornerRadius, spec.edgeX, spec.edgeY].every(finiteNonNegative);
    add('plate.numeric', 'Dimensions are finite and physical', dimensionsValid, 'All dimensions are positive; radius and offsets are non-negative.', 'Dimensions must be finite; width, height, thickness, and hole diameter must be greater than zero.');

    const cornerValid = finiteNonNegative(spec.cornerRadius) && spec.cornerRadius <= Math.min(spec.width, spec.height) / 2;
    add('plate.corner', 'Corner radius fits plate', cornerValid, `R${fmt(spec.cornerRadius)}`, 'Corner radius exceeds half of the smaller plate dimension.');

    const holeFits = finitePositive(spec.holeDiameter)
      && spec.edgeX >= spec.holeDiameter / 2
      && spec.edgeY >= spec.holeDiameter / 2
      && spec.edgeX <= spec.width - spec.holeDiameter / 2
      && spec.edgeY <= spec.height - spec.holeDiameter / 2;
    add('plate.hole-boundary', 'Hole pattern remains inside boundary', holeFits, 'All four hole profiles remain within the plate.', 'A hole crosses or touches the outer plate boundary. Increase the offset or reduce the hole diameter.');

    const horizontalGap = spec.width - 2 * spec.edgeX - spec.holeDiameter;
    const verticalGap = spec.height - 2 * spec.edgeY - spec.holeDiameter;
    const separated = horizontalGap > 0 && verticalGap > 0;
    add('plate.hole-spacing', 'Hole profiles do not overlap', separated, `Minimum axial gaps: ${fmt(horizontalGap)} × ${fmt(verticalGap)} ${spec.units}.`, 'Opposing holes overlap or touch.');

    const slenderness = spec.thickness <= Math.max(spec.width, spec.height);
    add('plate.proportion', 'Thickness is within template boundary', slenderness, 'Thickness can be represented by the plate template.', 'Thickness exceeds both face dimensions; use a different part template.');
  }

  if (spec.partType === 'flange') {
    const values = [spec.outerDiameter, spec.boreDiameter, spec.thickness, spec.boltCircleDiameter, spec.boltHoleDiameter, spec.boltCount];
    add('flange.numeric', 'Dimensions are finite and physical', values.every(finitePositive), 'All dimensions and bolt count are positive.', 'All dimensions and bolt count must be finite and greater than zero.');
    add('flange.bolt-count', 'Bolt count is an integer', Number.isInteger(spec.boltCount) && spec.boltCount >= 2 && spec.boltCount <= 64, `${spec.boltCount} equally spaced holes.`, 'Bolt count must be an integer from 2 through 64.');
    add('flange.diameter-order', 'Diameter hierarchy is valid', spec.outerDiameter > spec.boltCircleDiameter && spec.boltCircleDiameter > spec.boreDiameter, 'OD > PCD > bore.', 'Required order is outer diameter > bolt-circle diameter > bore diameter.');

    const outerClearance = (spec.outerDiameter - spec.boltCircleDiameter - spec.boltHoleDiameter) / 2;
    const innerClearance = (spec.boltCircleDiameter - spec.boltHoleDiameter - spec.boreDiameter) / 2;
    add('flange.radial-clearance', 'Bolt holes clear inner and outer profiles', outerClearance > 0 && innerClearance > 0, `Radial clearances: outside ${fmt(outerClearance)}, inside ${fmt(innerClearance)} ${spec.units}.`, 'Bolt holes intersect the bore or outer boundary.');

    const adjacentChord = spec.boltCircleDiameter * Math.sin(Math.PI / Math.max(spec.boltCount, 2));
    add('flange.hole-spacing', 'Adjacent bolt holes do not overlap', adjacentChord > spec.boltHoleDiameter, `Adjacent center spacing ${fmt(adjacentChord)} ${spec.units}.`, 'Adjacent bolt holes overlap or touch.');
  }

  if (spec.partType === 'shaft') {
    const allPositive = spec.segments.length === 3 && spec.segments.every((segment) => finitePositive(segment.length) && finitePositive(segment.diameter));
    add('shaft.numeric', 'Segment dimensions are finite and physical', allPositive, 'Three positive shaft segments defined.', 'Every shaft segment requires a positive length and diameter.');
    const totalLength = spec.segments.reduce((sum, segment) => sum + segment.length, 0);
    add('shaft.total-length', 'Overall length is valid', finitePositive(totalLength), `Overall length ${fmt(totalLength)} ${spec.units}.`, 'Overall length must be positive.');
    const ratio = totalLength / Math.max(...spec.segments.map((segment) => segment.diameter), 1);
    add('shaft.template-ratio', 'Geometry fits drawing template', ratio >= 0.25 && ratio <= 100, `Length-to-maximum-diameter ratio ${fmt(ratio)}.`, 'Geometry is outside the supported shaft-template aspect-ratio range (0.25–100).');
    const stepChanges = spec.segments[0].diameter !== spec.segments[1].diameter || spec.segments[1].diameter !== spec.segments[2].diameter;
    checks.push({
      id: 'shaft.step-definition',
      label: 'Stepped profile declared',
      status: stepChanges ? 'pass' : 'warning',
      detail: stepChanges ? 'At least one diameter transition is present.' : 'All diameters are equal; output is a straight shaft.',
    });
  }

  const passCount = checks.filter((check) => check.status === 'pass').length;
  const failCount = checks.filter((check) => check.status === 'fail').length;
  const warningCount = checks.filter((check) => check.status === 'warning').length;
  return { status: failCount === 0 ? 'validated' : 'rejected', checks, passCount, failCount, warningCount };
}

export async function buildArtifact(specInput: EngineeringSpec): Promise<GeneratedArtifact> {
  const spec = cloneSpec(specInput);
  const validation = validateSpecification(spec);
  if (validation.status !== 'validated') {
    const reasons = validation.checks.filter((check) => check.status === 'fail').map((check) => check.detail).join(' ');
    throw new Error(`Drawing rejected: ${reasons}`);
  }

  const specHash = await sha256Hex(canonicalJson(spec));
  const svg = renderDrawing(spec, specHash);
  const artifactHash = await sha256Hex(svg);
  const safeBase = `${safeFilename(spec.drawingNumber)}_REV-${safeFilename(spec.revision)}`;
  const manifest: ArtifactManifest = {
    schemaVersion: 'engidraw.manifest.v1',
    generator: { name: 'EngiDraw Verified', version: GENERATOR_VERSION },
    drawingNumber: spec.drawingNumber,
    revision: spec.revision,
    partType: spec.partType,
    standardProfile: spec.standard,
    units: spec.units,
    specHash,
    artifactHash,
    deterministic: true,
    validation,
    specification: spec,
    releaseState: 'VALIDATED_NOT_ENGINEER_APPROVED',
    disclaimer: 'Machine validation covers the checks listed in this manifest. A qualified engineer must approve safety-critical or production use.',
  };

  return {
    svg,
    manifest,
    svgFilename: `${safeBase}.svg`,
    manifestFilename: `${safeBase}.manifest.json`,
  };
}

export function interpretPrompt(promptInput: string): InterpretationResult {
  const prompt = promptInput.trim();
  if (!prompt) return { specification: null, matchedFields: [], errors: ['Enter a description.'] };

  const type: PartType = /\bflange\b/i.test(prompt) ? 'flange' : /\bshaft\b/i.test(prompt) ? 'shaft' : /\bplate\b/i.test(prompt) ? 'plate' : 'plate';
  const spec = cloneSpec(DEFAULT_SPECS[type]);
  const matchedFields: string[] = [];
  const errors: string[] = [];

  if (/\b(in|inch|inches)\b/i.test(prompt)) { spec.units = 'in'; matchedFields.push('units'); }
  if (/\bISO\b/i.test(prompt)) { spec.standard = 'ISO-128-2022'; matchedFields.push('standard'); }
  if (/\bASME\b/i.test(prompt)) { spec.standard = 'ASME-Y14.5-2018-R2024'; matchedFields.push('standard'); }

  if (spec.partType === 'plate') {
    const dimensions = prompt.match(/(\d+(?:\.\d+)?)\s*(?:x|×)\s*(\d+(?:\.\d+)?)\s*(?:x|×)\s*(\d+(?:\.\d+)?)/i);
    if (dimensions) {
      spec.width = Number(dimensions[1]); spec.height = Number(dimensions[2]); spec.thickness = Number(dimensions[3]);
      matchedFields.push('width', 'height', 'thickness');
    } else errors.push('Use width × height × thickness for the plate size.');
    const hole = labeledNumber(prompt, ['hole diameter', 'hole dia', 'holes diameter', 'holes dia', 'Ø']);
    if (hole !== null) { spec.holeDiameter = hole; matchedFields.push('holeDiameter'); }
    const edge = labeledNumber(prompt, ['edge offset', 'edge']);
    if (edge !== null) { spec.edgeX = edge; spec.edgeY = edge; matchedFields.push('edgeX', 'edgeY'); }
    const radius = labeledNumber(prompt, ['corner radius', 'corner r']);
    if (radius !== null) { spec.cornerRadius = radius; matchedFields.push('cornerRadius'); }
  }

  if (spec.partType === 'flange') {
    assignLabeled(spec, 'outerDiameter', prompt, ['outer diameter', 'OD'], matchedFields);
    assignLabeled(spec, 'boreDiameter', prompt, ['bore diameter', 'bore', 'ID'], matchedFields);
    assignLabeled(spec, 'thickness', prompt, ['thickness', 'thick'], matchedFields);
    assignLabeled(spec, 'boltCircleDiameter', prompt, ['bolt circle diameter', 'bolt circle', 'PCD', 'BCD'], matchedFields);
    assignLabeled(spec, 'boltHoleDiameter', prompt, ['bolt hole diameter', 'bolt hole dia', 'hole diameter'], matchedFields);
    const count = prompt.match(/(\d+)\s*(?:x\s*)?(?:bolt\s*)?holes?/i);
    if (count) { spec.boltCount = Number(count[1]); matchedFields.push('boltCount'); }
    const required = ['outerDiameter', 'boreDiameter', 'thickness', 'boltCircleDiameter', 'boltHoleDiameter'];
    if (required.some((field) => !matchedFields.includes(field))) errors.push('Include OD, bore, thickness, PCD, and bolt-hole diameter for a complete flange definition.');
  }

  if (spec.partType === 'shaft') {
    const length = labeledNumber(prompt, ['overall length', 'length']);
    const diameter = labeledNumber(prompt, ['maximum diameter', 'max diameter', 'diameter', 'dia']);
    if (length !== null) {
      spec.segments = [
        { ...spec.segments[0], length: roundValue(length * 0.22) },
        { ...spec.segments[1], length: roundValue(length * 0.56) },
        { ...spec.segments[2], length: roundValue(length * 0.22) },
      ];
      matchedFields.push('overallLength');
    } else errors.push('Include the shaft overall length.');
    if (diameter !== null) {
      spec.segments = [
        { ...spec.segments[0], diameter: roundValue(diameter * 0.72) },
        { ...spec.segments[1], diameter },
        { ...spec.segments[2], diameter: roundValue(diameter * 0.72) },
      ];
      matchedFields.push('maximumDiameter');
    } else errors.push('Include the shaft maximum diameter.');
  }

  return { specification: spec, matchedFields: [...new Set(matchedFields)], errors };
}

function assignLabeled<T extends FlangeSpec, K extends keyof T>(spec: T, key: K, prompt: string, labels: string[], matched: string[]) {
  const value = labeledNumber(prompt, labels);
  if (value !== null) {
    (spec[key] as number) = value;
    matched.push(String(key));
  }
}

function labeledNumber(text: string, labels: string[]): number | null {
  for (const label of labels) {
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = text.match(new RegExp(`${escaped}\\s*(?:=|:)?\\s*(\\d+(?:\\.\\d+)?)`, 'i'));
    if (match) return Number(match[1]);
  }
  return null;
}

function renderDrawing(spec: EngineeringSpec, specHash: string): string {
  const content = spec.partType === 'plate' ? renderPlate(spec) : spec.partType === 'flange' ? renderFlange(spec) : renderShaft(spec);
  const projection = spec.standard.startsWith('ASME') ? 'THIRD ANGLE PROJECTION' : 'FIRST ANGLE PROJECTION';
  const title = `${xml(spec.name)} — ${xml(spec.drawingNumber)} revision ${xml(spec.revision)}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 1188 840" role="img" aria-labelledby="drawing-title drawing-desc">
  <title id="drawing-title">${title}</title>
  <desc id="drawing-desc">Deterministic ${xml(spec.partType)} engineering drawing generated from validated dimensions.</desc>
  <defs>
    <marker id="arrow-end" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L8,4 L0,8 z" fill="#234f44"/></marker>
    <marker id="arrow-start" markerWidth="8" markerHeight="8" refX="1" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M8,0 L0,4 L8,8 z" fill="#234f44"/></marker>
    <style>
      .object{fill:none;stroke:#111815;stroke-width:2.2;vector-effect:non-scaling-stroke}.thin{fill:none;stroke:#111815;stroke-width:1.15;vector-effect:non-scaling-stroke}.hidden{fill:none;stroke:#56615d;stroke-width:1;stroke-dasharray:8 5;vector-effect:non-scaling-stroke}.center{fill:none;stroke:#427467;stroke-width:1;stroke-dasharray:14 4 3 4;vector-effect:non-scaling-stroke}.dim{fill:none;stroke:#234f44;stroke-width:1.2;vector-effect:non-scaling-stroke}.dimline{fill:none;stroke:#234f44;stroke-width:1.2;marker-start:url(#arrow-start);marker-end:url(#arrow-end);vector-effect:non-scaling-stroke}.txt{fill:#111815;font-family:Arial,sans-serif;font-size:14px}.mono{fill:#111815;font-family:ui-monospace,Consolas,monospace;font-size:13px}.dimtxt{fill:#234f44;font-family:ui-monospace,Consolas,monospace;font-size:14px}.small{font-size:11px}.view{font-size:12px;font-weight:700;letter-spacing:1.2px}.note{font-size:12px}.validation{fill:#245f51;font-weight:700}
    </style>
  </defs>
  <rect width="1188" height="840" fill="#fff"/>
  <rect x="20" y="20" width="1148" height="800" class="object"/>
  <path d="M32 20v800M1156 20v800M20 32h1148M20 808h1148" class="thin"/>
  ${content}
  ${renderNotes(spec, projection)}
  ${renderTitleBlock(spec, specHash)}
</svg>`;
}

function renderPlate(spec: PlateSpec): string {
  const scale = Math.min(520 / spec.width, 350 / spec.height);
  const w = spec.width * scale;
  const h = spec.height * scale;
  const x0 = 335 - w / 2;
  const y0 = 295 - h / 2;
  const r = spec.cornerRadius * scale;
  const hr = spec.holeDiameter * scale / 2;
  const holes = [
    [x0 + spec.edgeX * scale, y0 + spec.edgeY * scale],
    [x0 + w - spec.edgeX * scale, y0 + spec.edgeY * scale],
    [x0 + w - spec.edgeX * scale, y0 + h - spec.edgeY * scale],
    [x0 + spec.edgeX * scale, y0 + h - spec.edgeY * scale],
  ];
  const sideScale = Math.min(230 / Math.max(spec.thickness, 1), 350 / spec.height);
  const sideW = Math.max(spec.thickness * sideScale, 8);
  const sideH = spec.height * sideScale;
  const sx = 805;
  const sy = 295 - sideH / 2;
  return `<g id="plate-view">
    <text x="${n(x0)}" y="${n(y0 - 34)}" class="txt view">FRONT VIEW · 4X Ø${fmt(spec.holeDiameter)} THRU</text>
    <rect x="${n(x0)}" y="${n(y0)}" width="${n(w)}" height="${n(h)}" rx="${n(r)}" class="object"/>
    ${holes.map(([cx, cy]) => `${centerMark(cx, cy, hr + 12)}<circle cx="${n(cx)}" cy="${n(cy)}" r="${n(hr)}" class="object"/>`).join('')}
    ${dimH(x0, x0 + w, y0 + h + 55, y0 + h, dimension(spec.width, spec.units))}
    ${dimV(y0, y0 + h, x0 - 58, x0, dimension(spec.height, spec.units))}
    ${dimH(x0, holes[0][0], y0 - 18, y0, dimension(spec.edgeX, spec.units), true)}
    ${dimV(y0, holes[0][1], x0 + 18, x0, dimension(spec.edgeY, spec.units), true)}
    ${leader(holes[1][0] + hr * 0.7, holes[1][1] - hr * 0.7, holes[1][0] + 100, holes[1][1] - 68, `4X Ø${fmt(spec.holeDiameter)} THRU`)}
    <text x="${sx}" y="${n(sy - 34)}" class="txt view">RIGHT SIDE</text>
    <rect x="${sx}" y="${n(sy)}" width="${n(sideW)}" height="${n(sideH)}" class="object"/>
    <path d="M${n(sx - 20)} ${n(295)}h${n(sideW + 40)}" class="center"/>
    ${dimH(sx, sx + sideW, sy + sideH + 55, sy + sideH, dimension(spec.thickness, spec.units))}
  </g>`;
}

function renderFlange(spec: FlangeSpec): string {
  const scale = 380 / spec.outerDiameter;
  const cx = 350;
  const cy = 292;
  const outerR = spec.outerDiameter * scale / 2;
  const boreR = spec.boreDiameter * scale / 2;
  const pcdR = spec.boltCircleDiameter * scale / 2;
  const holeR = spec.boltHoleDiameter * scale / 2;
  const holes = Array.from({ length: spec.boltCount }, (_, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / spec.boltCount;
    return [cx + pcdR * Math.cos(angle), cy + pcdR * Math.sin(angle)];
  });
  const sideScale = Math.min(320 / spec.outerDiameter, 190 / spec.thickness);
  const sideH = spec.outerDiameter * sideScale;
  const sideW = Math.max(spec.thickness * sideScale, 12);
  const sx = 820;
  const sy = cy - sideH / 2;
  const boreHalf = spec.boreDiameter * sideScale / 2;
  return `<g id="flange-view">
    <text x="${n(cx - outerR)}" y="${n(cy - outerR - 34)}" class="txt view">FRONT VIEW · ${spec.boltCount}X Ø${fmt(spec.boltHoleDiameter)} EQ SP</text>
    <circle cx="${cx}" cy="${cy}" r="${n(outerR)}" class="object"/>
    <circle cx="${cx}" cy="${cy}" r="${n(boreR)}" class="object"/>
    <circle cx="${cx}" cy="${cy}" r="${n(pcdR)}" class="hidden"/>
    ${centerMark(cx, cy, outerR + 18)}
    ${holes.map(([hx, hy]) => `${centerMark(hx, hy, holeR + 7)}<circle cx="${n(hx)}" cy="${n(hy)}" r="${n(holeR)}" class="object"/>`).join('')}
    ${dimH(cx - outerR, cx + outerR, cy + outerR + 58, cy + outerR, `Ø${fmt(spec.outerDiameter)} ${spec.units}`)}
    ${leader(cx - boreR * 0.7, cy - boreR * 0.7, cx - outerR - 75, cy - outerR + 30, `BORE Ø${fmt(spec.boreDiameter)}`)}
    ${leader(cx + pcdR * 0.7, cy + pcdR * 0.7, cx + outerR + 92, cy + outerR - 32, `PCD Ø${fmt(spec.boltCircleDiameter)}`)}
    <text x="${sx}" y="${n(sy - 34)}" class="txt view">SECTION A—A</text>
    <rect x="${sx}" y="${n(sy)}" width="${n(sideW)}" height="${n(sideH)}" class="object"/>
    <path d="M${sx} ${n(cy - boreHalf)}h${n(sideW)}M${sx} ${n(cy + boreHalf)}h${n(sideW)}" class="hidden"/>
    <path d="M${n(sx - 20)} ${cy}h${n(sideW + 40)}" class="center"/>
    ${dimH(sx, sx + sideW, sy + sideH + 55, sy + sideH, dimension(spec.thickness, spec.units))}
  </g>`;
}

function renderShaft(spec: ShaftSpec): string {
  const totalLength = spec.segments.reduce((sum, segment) => sum + segment.length, 0);
  const maxDiameter = Math.max(...spec.segments.map((segment) => segment.diameter));
  const scale = Math.min(620 / totalLength, 300 / maxDiameter);
  const x0 = 170;
  const cy = 292;
  let x = x0;
  const top: Array<[number, number]> = [];
  const bottom: Array<[number, number]> = [];
  const boundaries: number[] = [x0];
  spec.segments.forEach((segment) => {
    const half = segment.diameter * scale / 2;
    top.push([x, cy - half], [x + segment.length * scale, cy - half]);
    bottom.unshift([x + segment.length * scale, cy + half], [x, cy + half]);
    x += segment.length * scale;
    boundaries.push(x);
  });
  const path = [...top, ...bottom].map(([px, py], index) => `${index === 0 ? 'M' : 'L'}${n(px)} ${n(py)}`).join(' ') + ' Z';
  const maxHalf = maxDiameter * scale / 2;
  const dimY = cy + maxHalf + 65;
  const endCx = 965;
  const endR = maxDiameter * Math.min(260 / maxDiameter, scale) / 2;
  return `<g id="shaft-view">
    <text x="${x0}" y="${n(cy - maxHalf - 38)}" class="txt view">LONGITUDINAL VIEW</text>
    <path d="${path}" class="object"/>
    <path d="M${n(x0 - 28)} ${cy}H${n(x + 28)}" class="center"/>
    ${boundaries.slice(1, -1).map((bx) => `<path d="M${n(bx)} ${n(cy - maxHalf - 15)}V${n(cy + maxHalf + 15)}" class="thin"/>`).join('')}
    ${spec.segments.map((segment, index) => {
      const centerX = (boundaries[index] + boundaries[index + 1]) / 2;
      const topY = cy - segment.diameter * scale / 2;
      return leader(centerX, topY, centerX + (index - 1) * 16, topY - 55, `Ø${fmt(segment.diameter)}`);
    }).join('')}
    ${spec.segments.map((segment, index) => dimH(boundaries[index], boundaries[index + 1], dimY, cy + maxHalf, dimension(segment.length, spec.units), true)).join('')}
    ${dimH(x0, x, dimY + 52, cy + maxHalf, `OVERALL ${dimension(totalLength, spec.units)}`)}
    <text x="${n(endCx - endR)}" y="${n(cy - endR - 34)}" class="txt view">END VIEW</text>
    <circle cx="${endCx}" cy="${cy}" r="${n(endR)}" class="object"/>
    ${centerMark(endCx, cy, endR + 18)}
  </g>`;
}

function renderNotes(spec: EngineeringSpec, projection: string): string {
  const decimal = spec.units === 'mm' ? 'TWO PLACE ±0.10 / THREE PLACE ±0.050' : 'TWO PLACE ±.01 / THREE PLACE ±.005';
  return `<g id="general-notes" class="txt note">
    <text x="54" y="625" class="view">GENERAL NOTES</text>
    <text x="54" y="648">1. DIMENSIONS ARE IN ${spec.units === 'mm' ? 'MILLIMETRES' : 'INCHES'}.</text>
    <text x="54" y="669">2. DO NOT SCALE DRAWING.</text>
    <text x="54" y="690">3. REMOVE BURRS AND BREAK SHARP EDGES.</text>
    <text x="360" y="648">4. UNLESS OTHERWISE SPECIFIED: ${decimal}.</text>
    <text x="360" y="669">5. MATERIAL: ${xml(spec.material)}.</text>
    <text x="360" y="690">6. ${projection}.</text>
  </g>`;
}

function renderTitleBlock(spec: EngineeringSpec, hash: string): string {
  return `<g id="title-block" transform="translate(720 720)">
    <rect width="448" height="100" class="object"/>
    <path d="M0 32h448M0 70h448M292 0v100M360 0v100M108 70v30M210 70v30" class="thin"/>
    <text x="12" y="21" class="txt view">ENGIDRAW VERIFIED</text>
    <text x="304" y="20" class="txt small validation">✓ MACHINE VALIDATED</text>
    <text x="12" y="56" class="txt" style="font-size:18px;font-weight:700">${xml(spec.name)}</text>
    <text x="300" y="49" class="txt small">DRAWING NO.</text><text x="300" y="64" class="mono">${xml(spec.drawingNumber)}</text>
    <text x="370" y="49" class="txt small">REV</text><text x="386" y="64" class="mono">${xml(spec.revision)}</text>
    <text x="10" y="84" class="txt small">STANDARD</text><text x="10" y="96" class="mono small">${xml(spec.standard)}</text>
    <text x="116" y="84" class="txt small">UNITS</text><text x="116" y="96" class="mono small">${spec.units}</text>
    <text x="218" y="84" class="txt small">SCALE</text><text x="218" y="96" class="mono small">AUTO</text>
    <text x="300" y="84" class="txt small">SPEC HASH</text><text x="300" y="96" class="mono small">${hash.slice(0, 14).toUpperCase()}</text>
  </g>`;
}

function dimH(x1: number, x2: number, y: number, objectY: number, label: string, compact = false): string {
  const offset = compact ? 7 : 12;
  return `<g><path d="M${n(x1)} ${n(objectY)}V${n(y + offset)}M${n(x2)} ${n(objectY)}V${n(y + offset)}" class="dim"/><path d="M${n(x1)} ${n(y)}H${n(x2)}" class="dimline"/><rect x="${n((x1 + x2) / 2 - label.length * 4.3)}" y="${n(y - 10)}" width="${n(label.length * 8.6)}" height="18" fill="white"/><text x="${n((x1 + x2) / 2)}" y="${n(y + 5)}" text-anchor="middle" class="dimtxt">${xml(label)}</text></g>`;
}

function dimV(y1: number, y2: number, x: number, objectX: number, label: string, compact = false): string {
  const offset = compact ? 7 : 12;
  const cy = (y1 + y2) / 2;
  return `<g><path d="M${n(objectX)} ${n(y1)}H${n(x - offset)}M${n(objectX)} ${n(y2)}H${n(x - offset)}" class="dim"/><path d="M${n(x)} ${n(y1)}V${n(y2)}" class="dimline"/><g transform="rotate(-90 ${n(x)} ${n(cy)})"><rect x="${n(x - label.length * 4.3)}" y="${n(cy - 10)}" width="${n(label.length * 8.6)}" height="18" fill="white"/><text x="${n(x)}" y="${n(cy + 5)}" text-anchor="middle" class="dimtxt">${xml(label)}</text></g></g>`;
}

function leader(x1: number, y1: number, x2: number, y2: number, label: string): string {
  const direction = x2 >= x1 ? 1 : -1;
  return `<g><path d="M${n(x1)} ${n(y1)}L${n(x2)} ${n(y2)}h${direction * 70}" class="dim" marker-start="url(#arrow-start)"/><text x="${n(x2 + direction * 4)}" y="${n(y2 - 7)}" text-anchor="${direction > 0 ? 'start' : 'end'}" class="dimtxt">${xml(label)}</text></g>`;
}

function centerMark(cx: number, cy: number, radius: number): string {
  return `<path d="M${n(cx - radius)} ${n(cy)}H${n(cx + radius)}M${n(cx)} ${n(cy - radius)}V${n(cy + radius)}" class="center"/>`;
}

function dimension(value: number, units: UnitSystem): string {
  return `${fmt(value)} ${units}`;
}

function fmt(value: number): string {
  if (!Number.isFinite(value)) return '—';
  return value.toFixed(2);
}

function n(value: number): string {
  return Number.isFinite(value) ? String(Math.round(value * 100) / 100) : '0';
}

function roundValue(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function xml(value: string): string {
  return value.replace(/[<>&"']/g, (character) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' })[character] ?? character);
}

function safeFilename(value: string): string {
  const safe = value.trim().replace(/[^a-z0-9._-]+/gi, '-').replace(/^-+|-+$/g, '');
  return safe || 'DRAWING';
}

function canonicalJson(value: unknown): string {
  return JSON.stringify(sortObject(value));
}

function sortObject(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortObject);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, sortObject(item)]));
  }
  return value;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('');
}
