# Public source snapshot

This folder contains 85 source, configuration, example, and test files from the 86-file tracked EngiDraw Verified project snapshot dated August 31, 2026. The private hosting configuration is excluded. A publication note and a drawing exported from the running app are included alongside the source. Local dependency folders and build output are not included.

The original Vite configuration imported `.openai/hosting.json`, a private workspace file. It is not included in this public copy. The public `vite.config.ts` now loads that file only when it is present. Without it, local development starts without the optional Cloudflare D1 and R2 bindings. No credentials or personal contact details from the private configuration are included here.

The public `lib/engidraw.ts` also includes a small drawing-layout correction: the title-block columns were adjusted so the drawing number, revision, standard label, and specification hash do not overlap in the exported sample. The full standard profile remains in the evidence manifest; the compact drawing field shows `ASME Y14.5` or `ISO 128`.

The existing project README describes a working MVP and lists test and build commands. Those commands were not run during this publication pass, so the current public copy has not been independently rebuilt or tested here.

The source README states the engineering limits: passing its automated checks does not certify safety, compliance, manufacturability, or physical performance. The gyroid component is a research demonstration, not a qualified heat exchanger.
