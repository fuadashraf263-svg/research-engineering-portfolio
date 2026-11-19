import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildArtifact,
  cloneSpec,
  DEFAULT_SPECS,
  interpretPrompt,
  validateSpecification,
  type PlateSpec,
} from '../lib/engidraw.ts';
import {
  buildGyroidArtifact,
  DEFAULT_GYROID_SPEC,
  validateGyroidSpecification,
} from '../lib/computational.ts';

void test('all mechanical templates generate validated SVG artifacts', async () => {
  for (const specification of Object.values(DEFAULT_SPECS)) {
    const artifact = await buildArtifact(specification);
    assert.equal(artifact.manifest.validation.status, 'validated');
    assert.match(artifact.svg, /^<svg/);
    assert.match(artifact.svg, /MACHINE VALIDATED/);
    assert.equal(artifact.manifest.specification.partType, specification.partType);
    assert.equal(artifact.manifest.artifactHash.length, 64);
  }
});

void test('mechanical generation is deterministic for identical inputs', async () => {
  const first = await buildArtifact(DEFAULT_SPECS.flange);
  const second = await buildArtifact(cloneSpec(DEFAULT_SPECS.flange));
  assert.equal(first.svg, second.svg);
  assert.equal(first.manifest.specHash, second.manifest.specHash);
  assert.equal(first.manifest.artifactHash, second.manifest.artifactHash);
});

void test('plate validation rejects holes outside the part boundary', () => {
  const invalid = { ...cloneSpec(DEFAULT_SPECS.plate), holeDiameter: 30, edgeX: 10 } as PlateSpec;
  const report = validateSpecification(invalid);
  assert.equal(report.status, 'rejected');
  assert.ok(report.checks.some((check) => check.id === 'plate.hole-boundary' && check.status === 'fail'));
});

void test('flange interpreter extracts labeled dimensions without guessing', () => {
  const result = interpretPrompt('Flange OD 160, bore 60, thickness 18, PCD 120, 8 bolt holes, bolt hole diameter 12, ISO');
  assert.equal(result.errors.length, 0);
  assert.equal(result.specification?.partType, 'flange');
  if (result.specification?.partType !== 'flange') assert.fail('Expected flange specification');
  assert.equal(result.specification.outerDiameter, 160);
  assert.equal(result.specification.boltCount, 8);
  assert.equal(result.specification.standard, 'ISO-128-2022');
});

void test('computational kernel creates a deterministic implicit STL mesh', async () => {
  const specification = { ...DEFAULT_GYROID_SPEC, resolution: 16, wallThickness: 4 };
  const first = await buildGyroidArtifact(specification);
  const second = await buildGyroidArtifact({ ...specification });
  assert.ok(first.mesh.length > 1_000);
  assert.match(first.stl, /^solid ED-CEM-001/);
  assert.match(first.stl, /endsolid ED-CEM-001$/);
  assert.equal(first.recipe.meshHash, second.recipe.meshHash);
  assert.equal(first.recipe.releaseState, 'RESEARCH_GEOMETRY_NOT_PHYSICS_VALIDATED');
});

void test('computational validation blocks under-resolved geometry', () => {
  const report = validateGyroidSpecification({ ...DEFAULT_GYROID_SPEC, resolution: 16, wallThickness: 1 });
  assert.equal(report.status, 'rejected');
  assert.ok(report.checks.some((check) => check.id === 'cem.discretization' && check.status === 'fail'));
});
