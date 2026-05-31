from __future__ import annotations

from pydantic import BaseModel

from mimir.core.errors import NormalizationError
from mimir.core.normalize import normalize
from mimir.core.registry import Registry
from mimir.core.source import Cadence, FetchContext, Source
from mimir.manifest.manifest import Manifest, SourceResult
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record


class RunSummary(BaseModel):
    cadence: Cadence
    results: list[SourceResult]

    @property
    def had_failures(self) -> bool:
        return any(not r.ok for r in self.results)


class Orchestrator:
    def __init__(self, registry: Registry, store: JsonlStore, manifest: Manifest) -> None:
        self._registry = registry
        self._store = store
        self._manifest = manifest

    def run(self, cadence: Cadence, ctx: FetchContext) -> RunSummary:
        results = [self._run_one(source, ctx) for source in self._registry.due(cadence)]
        self._manifest.write(now=ctx.now, cadence=cadence, results=results)
        return RunSummary(cadence=cadence, results=results)

    def _run_one(self, source: Source, ctx: FetchContext) -> SourceResult:
        try:
            raws = list(source.fetch(ctx))
            records: list[Record] = []
            invalid = 0
            for raw in raws:
                try:
                    records.append(normalize(raw, source.meta, captured_at=ctx.now))
                except NormalizationError:  # one bad record must not lose the rest
                    invalid += 1
            stored = self._store.append(records)
            return SourceResult(
                source=source.meta.id, ok=True, fetched=len(raws), stored=stored, invalid=invalid
            )
        except Exception as exc:  # source isolation: never let one source kill the run
            return SourceResult(source=source.meta.id, ok=False, error=str(exc))
