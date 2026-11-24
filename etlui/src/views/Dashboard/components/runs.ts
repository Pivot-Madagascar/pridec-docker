import type { InjectionKey } from 'vue'
import type { Checkpoints, Disease, Source } from '@/types/pipeline'
import type { DefaultFile, InputName, PreviewFrom, ServerFile } from '@/types/inputs'

// ForecastRuns provides its props and emit to every LevelColumn, instead of relaying them through DiseaseCard.
// The breadcrumb's "go to the current item" in step ②: the open run shows it (`at` makes each click a new request).
export interface RunFocus {
  item: string
  blink: boolean
  at: number
}

export interface RunsProps {
  state: Checkpoints | null
  focus?: RunFocus | null
  busy: boolean
  serverFiles: Partial<Record<InputName, ServerFile>>
  defaults: Record<string, DefaultFile>
  // Returns true once uploaded: the selected file is then cleared.
  uploadFile: (name: InputName, file: File) => Promise<boolean>
  // The open run's input/ as a zip: the files the forecast computation will read.
  inputArchiveUrl: string
}

export interface RunsEmit {
  (e: 'open' | 'report', source: Source, disease: Disease): void
  (e: 'launch', item: string): void
  (e: 'validate' | 'abandon' | 'skip'): void // skip: calc_orgunit_alerts marked done without computing (skip_alerts)
  (e: 'delete' | 'use-default', name: InputName): void
  (e: 'preview', name: InputName, from: PreviewFrom): void
}

export const RUNS: InjectionKey<{ props: RunsProps; emit: RunsEmit }> = Symbol('runs')
