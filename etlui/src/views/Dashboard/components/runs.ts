import type { InjectionKey } from 'vue'
import type { Checkpoints, Disease, Source } from '@/types/pipeline'
import type { DefaultFile, InputName, PreviewFrom, ServerFile } from '@/types/inputs'

// ForecastRuns provides its props and emit to every LevelColumn, instead of relaying them through DiseaseCard.
export interface RunsProps {
  state: Checkpoints | null
  busy: boolean
  serverFiles: Partial<Record<InputName, ServerFile>>
  defaults: Record<string, DefaultFile>
  // Returns true once uploaded: the selected file is then cleared.
  uploadFile: (name: InputName, file: File) => Promise<boolean>
}

export interface RunsEmit {
  (e: 'open' | 'report', source: Source, disease: Disease): void
  (e: 'launch', item: string): void
  (e: 'validate'): void
  (e: 'delete' | 'use-default', name: InputName): void
  (e: 'preview', name: InputName, from: PreviewFrom): void
}

export const RUNS: InjectionKey<{ props: RunsProps; emit: RunsEmit }> = Symbol('runs')
