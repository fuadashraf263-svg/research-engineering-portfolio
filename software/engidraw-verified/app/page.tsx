'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';
import {
  Box,
  Braces,
  Check,
  CheckCircle2,
  CircleDot,
  Clipboard,
  Download,
  FileCode2,
  Gauge,
  Hexagon,
  LoaderCircle,
  Maximize2,
  Printer,
  Rotate3D,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  X,
} from 'lucide-react';
import {
  buildArtifact,
  cloneSpec,
  DEFAULT_SPECS,
  type EngineeringSpec,
  type FlangeSpec,
  type GeneratedArtifact,
  interpretPrompt,
  type PartType,
  type PlateSpec,
  type ShaftSpec,
  validateSpecification,
} from '@/lib/engidraw';
import {
  buildGyroidArtifact,
  type ComputationalArtifact,
  DEFAULT_GYROID_SPEC,
  drawMesh,
  type GyroidSpec,
  validateGyroidSpecification,
} from '@/lib/computational';

type Mode = PartType | 'gyroid';

const MODE_META: Array<{ id: Mode; label: string; detail: string; icon: typeof Box }> = [
  { id: 'plate', label: 'Plate', detail: '4-hole detail', icon: Box },
  { id: 'flange', label: 'Flange', detail: 'Bolt pattern', icon: CircleDot },
  { id: 'shaft', label: 'Shaft', detail: '3-step profile', icon: Gauge },
  { id: 'gyroid', label: 'CEM core', detail: 'Implicit 3D', icon: Rotate3D },
];

const EXAMPLE_PROMPTS = [
  'Plate 120 × 80 × 10 mm, hole diameter 8, edge offset 15, corner radius 5, ASME',
  'Flange OD 160, bore 60, thickness 18, PCD 120, 8 bolt holes, bolt hole diameter 12, ISO',
  'Stepped shaft overall length 140 mm, maximum diameter 45, ASME',
];

export default function Home() {
  const [mode, setMode] = useState<Mode>('plate');
  const [spec, setSpec] = useState<EngineeringSpec>(() => cloneSpec(DEFAULT_SPECS.plate));
  const [gyroid, setGyroid] = useState<GyroidSpec>(() => ({ ...DEFAULT_GYROID_SPEC }));
  const [artifact, setArtifact] = useState<GeneratedArtifact | null>(null);
  const [computationalArtifact, setComputationalArtifact] = useState<ComputationalArtifact | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');
  const [prompt, setPrompt] = useState(EXAMPLE_PROMPTS[0]);
  const [interpretation, setInterpretation] = useState('');
  const [zoom, setZoom] = useState(1);

  const validation = useMemo(
    () => mode === 'gyroid' ? validateGyroidSpecification(gyroid) : validateSpecification(spec),
    [mode, gyroid, spec],
  );

  useEffect(() => {
    buildArtifact(cloneSpec(DEFAULT_SPECS.plate)).then(setArtifact).catch((caught: Error) => setError(caught.message));
  }, []);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError('');
    setInterpretation('');
    setDirty(true);
    setZoom(1);
    if (next !== 'gyroid') setSpec(cloneSpec(DEFAULT_SPECS[next]));
  };

  const updateSpec = (next: EngineeringSpec) => {
    setSpec(next);
    setDirty(true);
    setError('');
  };

  const updateGyroid = (patch: Partial<GyroidSpec>) => {
    setGyroid((current) => ({ ...current, ...patch }));
    setDirty(true);
    setError('');
  };

  const generate = async () => {
    setError('');
    if (validation.status === 'rejected') {
      setError('Generation stopped. Resolve the failed validation checks first.');
      return;
    }
    setIsGenerating(true);
    try {
      if (mode === 'gyroid') {
        const result = await buildGyroidArtifact(gyroid);
        setComputationalArtifact(result);
      } else {
        const result = await buildArtifact(spec);
        setArtifact(result);
      }
      setDirty(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  const runInterpreter = () => {
    const result = interpretPrompt(prompt);
    if (!result.specification) {
      setInterpretation(result.errors.join(' '));
      return;
    }
    setMode(result.specification.partType);
    setSpec(result.specification);
    setDirty(true);
    setError('');
    setInterpretation(`${result.matchedFields.length} fields recognized.${result.errors.length ? ` ${result.errors.join(' ')}` : ' Ready to validate.'}`);
  };

  const activeDrawing = mode === 'gyroid' ? null : artifact;
  const activeComputational = mode === 'gyroid' ? computationalArtifact : null;

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-card/95 px-4 backdrop-blur sm:px-5">
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-md bg-primary text-primary-foreground shadow-sm">
            <Hexagon className="size-4" />
          </span>
          <div>
            <p className="text-sm font-semibold leading-none">EngiDraw</p>
            <p className="mt-1 text-[9px] font-semibold uppercase tracking-[0.19em] text-muted-foreground">Verified computational engineering</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="hidden gap-1.5 border-primary/25 bg-primary/5 text-primary sm:flex">
            <span className="size-1.5 rounded-full bg-emerald-500" /> Deterministic kernel
          </Badge>
          <Badge variant="secondary">v0.1 MVP</Badge>
        </div>
      </header>

      <div className="grid min-h-[calc(100vh-3.5rem)] grid-cols-[350px_minmax(0,1fr)_290px] 2xl:grid-cols-[380px_minmax(0,1fr)_320px] max-xl:grid-cols-[340px_minmax(0,1fr)] max-md:grid-cols-1">
        <aside className="border-r bg-card max-md:border-b max-md:border-r-0">
          <div className="border-b p-4 sm:p-5">
            <p className="eyebrow">Model family</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {MODE_META.map((item) => {
                const Icon = item.icon;
                const selected = mode === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => switchMode(item.id)}
                    aria-pressed={selected}
                    className={`model-card ${selected ? 'model-card-active' : ''}`}
                  >
                    <Icon className="size-4" />
                    <span><strong>{item.label}</strong><small>{item.detail}</small></span>
                  </button>
                );
              })}
            </div>
          </div>

          {mode !== 'gyroid' && (
            <div className="border-b p-4 sm:p-5">
              <div className="flex items-center justify-between">
                <p className="eyebrow">Intent interpreter</p>
                <Badge variant="outline" className="text-[9px]">Constrained</Badge>
              </div>
              <Textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                className="mt-3 min-h-20 resize-none font-mono text-[11px] leading-5"
                aria-label="Natural language part description"
              />
              <div className="mt-2 flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={runInterpreter}><Sparkles /> Interpret</Button>
                <button type="button" className="text-[10px] font-medium text-muted-foreground underline-offset-2 hover:underline" onClick={() => setPrompt(EXAMPLE_PROMPTS[(EXAMPLE_PROMPTS.indexOf(prompt) + 1) % EXAMPLE_PROMPTS.length])}>Next example</button>
              </div>
              {interpretation && <p className="mt-2 text-[10px] leading-4 text-muted-foreground">{interpretation}</p>}
            </div>
          )}

          <div className="p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="eyebrow">Parameters</p>
                <h1 className="mt-1 text-lg font-semibold tracking-tight">{mode === 'gyroid' ? gyroid.name : spec.name}</h1>
              </div>
              {mode === 'gyroid' && <Badge className="bg-[#5939a8] text-white">Advanced</Badge>}
            </div>

            {mode === 'gyroid' ? (
              <GyroidFields spec={gyroid} onChange={updateGyroid} />
            ) : (
              <MechanicalFields spec={spec} onChange={updateSpec} />
            )}

            <div className="mt-5 grid grid-cols-2 gap-3 border-t pt-4">
              <Field label="Drawing number">
                <Input value={mode === 'gyroid' ? gyroid.drawingNumber : spec.drawingNumber} onChange={(event) => mode === 'gyroid' ? updateGyroid({ drawingNumber: event.target.value }) : updateSpec({ ...spec, drawingNumber: event.target.value })} />
              </Field>
              <Field label="Revision">
                <Input value={mode === 'gyroid' ? gyroid.revision : spec.revision} onChange={(event) => mode === 'gyroid' ? updateGyroid({ revision: event.target.value }) : updateSpec({ ...spec, revision: event.target.value })} />
              </Field>
              <Field label="Units">
                <NativeSelect className="w-full" value={mode === 'gyroid' ? gyroid.units : spec.units} onChange={(event) => mode === 'gyroid' ? updateGyroid({ units: event.target.value as 'mm' | 'in' }) : updateSpec({ ...spec, units: event.target.value as 'mm' | 'in' })}>
                  <NativeSelectOption value="mm">Millimetres</NativeSelectOption>
                  <NativeSelectOption value="in">Inches</NativeSelectOption>
                </NativeSelect>
              </Field>
              <Field label="Standard">
                <NativeSelect className="w-full" value={mode === 'gyroid' ? gyroid.standard : spec.standard} onChange={(event) => mode === 'gyroid' ? updateGyroid({ standard: event.target.value as GyroidSpec['standard'] }) : updateSpec({ ...spec, standard: event.target.value as EngineeringSpec['standard'] })}>
                  <NativeSelectOption value="ASME-Y14.5-2018-R2024">ASME Y14.5</NativeSelectOption>
                  <NativeSelectOption value="ISO-128-2022">ISO 128</NativeSelectOption>
                </NativeSelect>
              </Field>
            </div>

            <Button className="mt-5 h-10 w-full" onClick={generate} disabled={isGenerating || validation.status === 'rejected'}>
              {isGenerating ? <><LoaderCircle className="animate-spin" /> Computing geometry…</> : <><ShieldCheck /> {mode === 'gyroid' ? 'Compile 3D model' : 'Generate validated drawing'}</>}
            </Button>
            {error && <div className="mt-3 flex gap-2 rounded-md border border-destructive/25 bg-destructive/5 p-2.5 text-[11px] leading-4 text-destructive"><ShieldAlert className="mt-0.5 size-3.5 shrink-0" />{error}</div>}
          </div>
        </aside>

        <section className="flex min-w-0 flex-col bg-workspace p-4 sm:p-6">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <p className="eyebrow">{mode === 'gyroid' ? 'Volumetric model' : 'Drawing sheet'}</p>
                {dirty && <Badge variant="outline" className="border-amber-500/40 bg-amber-100/70 text-[9px] text-amber-800">Parameters changed</Badge>}
              </div>
              <p className="mt-1 text-sm font-semibold">{mode === 'gyroid' ? gyroid.drawingNumber : spec.drawingNumber} · Revision {mode === 'gyroid' ? gyroid.revision : spec.revision}</p>
            </div>
            <div className="flex items-center gap-1.5">
              {mode !== 'gyroid' && (
                <>
                  <Button variant="outline" size="icon-sm" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(.65, value - .1))}>−</Button>
                  <span className="w-11 text-center font-mono text-[10px]">{Math.round(zoom * 100)}%</span>
                  <Button variant="outline" size="icon-sm" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.6, value + .1))}>+</Button>
                  <Button variant="outline" size="icon-sm" aria-label="Fit drawing" onClick={() => setZoom(1)}><Maximize2 /></Button>
                </>
              )}
            </div>
          </div>

          <div className="relative grid min-h-[440px] flex-1 place-items-center overflow-auto rounded-md border border-black/15 bg-[#dfe4e2] p-3 shadow-inner">
            {mode === 'gyroid' ? (
              activeComputational ? <ComputationalPreview artifact={activeComputational} /> : <EmptyPreview mode="gyroid" />
            ) : activeDrawing ? (
              <div className="drawing-sheet" style={{ width: `${zoom * 100}%` }} dangerouslySetInnerHTML={{ __html: activeDrawing.svg }} />
            ) : <EmptyPreview mode={mode} />}
          </div>

          <ArtifactToolbar mode={mode} drawing={activeDrawing} computational={activeComputational} specification={mode === 'gyroid' ? gyroid : spec} />
        </section>

        <ValidationPanel validation={validation} mode={mode} computational={activeComputational} dirty={dirty} />
      </div>
    </main>
  );
}

function MechanicalFields({ spec, onChange }: { spec: EngineeringSpec; onChange: (spec: EngineeringSpec) => void }) {
  if (spec.partType === 'plate') {
    return <div className="mt-4 grid grid-cols-2 gap-3">
      <NumberField label="Width" value={spec.width} units={spec.units} onChange={(width) => onChange({ ...spec, width })} />
      <NumberField label="Height" value={spec.height} units={spec.units} onChange={(height) => onChange({ ...spec, height })} />
      <NumberField label="Thickness" value={spec.thickness} units={spec.units} onChange={(thickness) => onChange({ ...spec, thickness })} />
      <NumberField label="Corner radius" value={spec.cornerRadius} units={spec.units} onChange={(cornerRadius) => onChange({ ...spec, cornerRadius })} />
      <NumberField label="Hole diameter" value={spec.holeDiameter} units={spec.units} onChange={(holeDiameter) => onChange({ ...spec, holeDiameter })} />
      <NumberField label="X edge offset" value={spec.edgeX} units={spec.units} onChange={(edgeX) => onChange({ ...spec, edgeX })} />
      <NumberField label="Y edge offset" value={spec.edgeY} units={spec.units} onChange={(edgeY) => onChange({ ...spec, edgeY })} />
      <MaterialField value={spec.material} onChange={(material) => onChange({ ...spec, material } as PlateSpec)} />
    </div>;
  }
  if (spec.partType === 'flange') {
    return <div className="mt-4 grid grid-cols-2 gap-3">
      <NumberField label="Outer diameter" value={spec.outerDiameter} units={spec.units} onChange={(outerDiameter) => onChange({ ...spec, outerDiameter })} />
      <NumberField label="Bore diameter" value={spec.boreDiameter} units={spec.units} onChange={(boreDiameter) => onChange({ ...spec, boreDiameter })} />
      <NumberField label="Thickness" value={spec.thickness} units={spec.units} onChange={(thickness) => onChange({ ...spec, thickness })} />
      <NumberField label="Bolt circle" value={spec.boltCircleDiameter} units={spec.units} onChange={(boltCircleDiameter) => onChange({ ...spec, boltCircleDiameter })} />
      <NumberField label="Bolt-hole diameter" value={spec.boltHoleDiameter} units={spec.units} onChange={(boltHoleDiameter) => onChange({ ...spec, boltHoleDiameter })} />
      <NumberField label="Bolt count" value={spec.boltCount} step={1} onChange={(boltCount) => onChange({ ...spec, boltCount })} />
      <MaterialField value={spec.material} onChange={(material) => onChange({ ...spec, material } as FlangeSpec)} wide />
    </div>;
  }
  return <div className="mt-4">
    <div className="grid grid-cols-[34px_1fr_1fr] gap-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground"><span>Step</span><span>Length</span><span>Diameter</span></div>
    <div className="mt-2 space-y-2">
      {spec.segments.map((segment, index) => <div key={index} className="grid grid-cols-[34px_1fr_1fr] items-center gap-2">
        <span className="grid size-7 place-items-center rounded bg-muted font-mono text-[11px]">{index + 1}</span>
        <Input type="number" min="0" step="any" value={safeValue(segment.length)} aria-label={`Segment ${index + 1} length`} onChange={(event) => onChange(updateSegment(spec, index, 'length', Number(event.target.value)))} />
        <Input type="number" min="0" step="any" value={safeValue(segment.diameter)} aria-label={`Segment ${index + 1} diameter`} onChange={(event) => onChange(updateSegment(spec, index, 'diameter', Number(event.target.value)))} />
      </div>)}
    </div>
    <div className="mt-3"><MaterialField value={spec.material} onChange={(material) => onChange({ ...spec, material } as ShaftSpec)} wide /></div>
  </div>;
}

function GyroidFields({ spec, onChange }: { spec: GyroidSpec; onChange: (patch: Partial<GyroidSpec>) => void }) {
  return <div className="mt-4 grid grid-cols-2 gap-3">
    <NumberField label="Width" value={spec.width} units={spec.units} onChange={(width) => onChange({ width })} />
    <NumberField label="Depth" value={spec.depth} units={spec.units} onChange={(depth) => onChange({ depth })} />
    <NumberField label="Height" value={spec.height} units={spec.units} onChange={(height) => onChange({ height })} />
    <NumberField label="Cell size" value={spec.cellSize} units={spec.units} onChange={(cellSize) => onChange({ cellSize })} />
    <NumberField label="Wall thickness" value={spec.wallThickness} units={spec.units} onChange={(wallThickness) => onChange({ wallThickness })} />
    <NumberField label="Grid resolution" value={spec.resolution} step={1} onChange={(resolution) => onChange({ resolution })} />
    <MaterialField value={spec.material} onChange={(material) => onChange({ material })} wide />
    <Field label="Manufacturing process" wide><Input value={spec.process} onChange={(event) => onChange({ process: event.target.value })} /></Field>
  </div>;
}

function ValidationPanel({ validation, mode, computational, dirty }: { validation: ReturnType<typeof validateSpecification>; mode: Mode; computational: ComputationalArtifact | null; dirty: boolean }) {
  return <aside className="border-l bg-card max-xl:col-span-2 max-xl:border-l-0 max-xl:border-t max-md:col-span-1">
    <div className="border-b p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <div><p className="eyebrow">Evidence</p><h2 className="mt-1 text-base font-semibold">Validation gates</h2></div>
        <Badge variant={validation.status === 'validated' ? 'secondary' : 'destructive'} className={validation.status === 'validated' ? 'bg-emerald-100 text-emerald-800' : ''}>
          {validation.status === 'validated' ? <CheckCircle2 /> : <ShieldAlert />} {validation.status}
        </Badge>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <Metric label="Passed" value={validation.passCount} tone="green" />
        <Metric label="Failed" value={validation.failCount} tone="red" />
        <Metric label="Warnings" value={validation.warningCount} tone="amber" />
      </div>
    </div>
    <div className="max-h-[470px] overflow-auto p-3 sm:p-4">
      <ul className="space-y-1.5">
        {validation.checks.map((check) => <li key={check.id} className={`check-row check-${check.status}`}>
          <span className="mt-0.5">{check.status === 'pass' ? <Check className="size-3.5" /> : check.status === 'fail' ? <X className="size-3.5" /> : <TriangleAlert className="size-3.5" />}</span>
          <span><strong>{check.label}</strong><small>{check.detail}</small></span>
        </li>)}
      </ul>
    </div>
    {mode === 'gyroid' && computational && <div className="border-t p-4">
      <p className="eyebrow">Mesh telemetry</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
        <Stat label="Triangles" value={computational.recipe.stats.triangleCount.toLocaleString()} />
        <Stat label="Grid spacing" value={`${computational.recipe.stats.gridSpacing.toFixed(2)} ${computational.recipe.specification.units}`} />
        <Stat label="Surface area" value={`${computational.recipe.stats.surfaceArea.toFixed(0)} ${computational.recipe.specification.units}²`} />
        <Stat label="Est. volume" value={`${computational.recipe.stats.estimatedSolidVolume.toFixed(0)} ${computational.recipe.specification.units}³`} />
      </dl>
    </div>}
    <div className="border-t bg-[#f1eee6] p-4 text-[10px] leading-4 text-[#5f584c]">
      <div className="flex gap-2"><ShieldAlert className="mt-0.5 size-3.5 shrink-0" /><p><strong>Release boundary:</strong> {mode === 'gyroid' ? 'Research geometry only. Thermal, flow, structural, pressure, and process validation remain mandatory.' : 'Machine-validated drawing, not engineer-approved. Production release requires qualified review.'}{dirty ? ' The preview is older than the current parameters.' : ''}</p></div>
    </div>
  </aside>;
}

function ArtifactToolbar({ mode, drawing, computational, specification }: { mode: Mode; drawing: GeneratedArtifact | null; computational: ComputationalArtifact | null; specification: EngineeringSpec | GyroidSpec }) {
  const copySpec = () => navigator.clipboard.writeText(JSON.stringify(specification, null, 2));
  return <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
      {mode === 'gyroid' ? <><Braces className="size-3.5" /> SDF → tetrahedral isosurface → STL</> : <><FileCode2 className="size-3.5" /> Semantic dimensions → deterministic SVG</>}
    </div>
    <div className="flex flex-wrap gap-2">
      <Button variant="outline" size="sm" onClick={copySpec}><Clipboard /> Copy spec</Button>
      {mode !== 'gyroid' && drawing && <>
        <Button variant="outline" size="sm" onClick={() => downloadText(drawing.svg, drawing.svgFilename, 'image/svg+xml')}><Download /> SVG</Button>
        <Button variant="outline" size="sm" onClick={() => downloadText(JSON.stringify(drawing.manifest, null, 2), drawing.manifestFilename, 'application/json')}><FileCode2 /> Manifest</Button>
        <Button variant="outline" size="sm" onClick={() => printSvg(drawing.svg)}><Printer /> Print / PDF</Button>
      </>}
      {mode === 'gyroid' && computational && <>
        <Button variant="outline" size="sm" onClick={() => downloadText(computational.stl, computational.stlFilename, 'model/stl')}><Download /> STL</Button>
        <Button variant="outline" size="sm" onClick={() => downloadText(JSON.stringify(computational.recipe, null, 2), computational.recipeFilename, 'application/json')}><FileCode2 /> CEM recipe</Button>
      </>}
    </div>
  </div>;
}

function ComputationalPreview({ artifact }: { artifact: ComputationalArtifact }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [angle, setAngle] = useState(.72);
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const redraw = () => drawMesh(element, artifact.mesh, -.55, angle);
    redraw();
    const observer = new ResizeObserver(redraw);
    observer.observe(element);
    return () => observer.disconnect();
  }, [artifact, angle]);
  return <div className="relative h-full min-h-[440px] w-full overflow-hidden rounded bg-[#f9fbfa]">
    <canvas ref={canvas} className="h-full min-h-[440px] w-full" aria-label="Generated gyroid thermal core mesh preview" />
    <div className="absolute left-3 top-3 rounded border border-primary/20 bg-white/90 px-2.5 py-2 shadow-sm backdrop-blur">
      <p className="font-mono text-[10px] font-semibold text-primary">IMPLICIT GYROID · ISO 0</p>
      <p className="mt-1 text-[9px] text-muted-foreground">{artifact.recipe.stats.triangleCount.toLocaleString()} triangles · research mesh</p>
    </div>
    <label className="absolute bottom-3 left-1/2 flex w-[min(360px,85%)] -translate-x-1/2 items-center gap-3 rounded border bg-white/90 px-3 py-2 text-[10px] font-medium shadow-sm backdrop-blur"><Rotate3D className="size-3.5" /><span>Rotate</span><input className="accent-primary w-full" type="range" min="-3.14" max="3.14" step="0.05" value={angle} onChange={(event) => setAngle(Number(event.target.value))} /></label>
  </div>;
}

function EmptyPreview({ mode }: { mode: Mode }) {
  return <div className="mx-auto max-w-sm text-center text-muted-foreground">
    <span className="mx-auto grid size-12 place-items-center rounded-full border bg-white"><Hexagon className="size-5" /></span>
    <p className="mt-3 text-sm font-semibold text-foreground">Compile the {mode === 'gyroid' ? 'volumetric model' : 'drawing'}</p>
    <p className="mt-1 text-xs leading-5">Validated output and downloadable evidence will appear here.</p>
  </div>;
}

function NumberField({ label, value, units, step = 'any', onChange }: { label: string; value: number; units?: string; step?: number | 'any'; onChange: (value: number) => void }) {
  return <Field label={label}><div className="relative"><Input type="number" min="0" step={step} value={safeValue(value)} onChange={(event) => onChange(Number(event.target.value))} className={units ? 'pr-10' : ''} />{units && <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 font-mono text-[9px] text-muted-foreground">{units}</span>}</div></Field>;
}

function MaterialField({ value, onChange, wide = false }: { value: string; onChange: (value: string) => void; wide?: boolean }) {
  return <Field label="Material" wide={wide}><Input value={value} onChange={(event) => onChange(event.target.value)} /></Field>;
}

function Field({ label, children, wide = false }: { label: string; children: React.ReactNode; wide?: boolean }) {
  return <label className={`field-label ${wide ? 'col-span-2' : ''}`}>{label}{children}</label>;
}

function Metric({ label, value, tone }: { label: string; value: number; tone: 'green' | 'red' | 'amber' }) {
  return <div className={`metric metric-${tone}`}><strong>{value}</strong><span>{label}</span></div>;
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</dt><dd className="mt-1 font-mono font-semibold">{value}</dd></div>;
}

function updateSegment(spec: ShaftSpec, index: number, key: 'length' | 'diameter', value: number): ShaftSpec {
  const segments = spec.segments.map((segment, segmentIndex) => segmentIndex === index ? { ...segment, [key]: value } : segment) as ShaftSpec['segments'];
  return { ...spec, segments };
}

function safeValue(value: number): number | '' { return Number.isFinite(value) ? value : ''; }

function downloadText(text: string, filename: string, mime: string) {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function printSvg(svg: string) {
  const popup = window.open('', '_blank');
  if (!popup) return;
  popup.opener = null;
  popup.document.title = 'EngiDraw print';
  const style = popup.document.createElement('style');
  style.textContent = 'body{margin:0}svg{width:100%;height:auto}@page{size:A3 landscape;margin:0}';
  popup.document.head.appendChild(style);
  popup.document.body.innerHTML = svg;
  setTimeout(() => popup.print(), 250);
}
