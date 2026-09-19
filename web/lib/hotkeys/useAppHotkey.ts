'use client'

// Isolates the @tanstack/react-hotkeys API (alpha, pinned exactly — see
// package.json) to this one file. If its shape changes across releases,
// this is the only place the rest of the app needs updating.

import {
  useHotkey,
  useHotkeySequences,
  type UseHotkeySequenceDefinition,
} from '@tanstack/react-hotkeys'
import type { HotkeyCallback, RegisterableHotkey } from '@tanstack/hotkeys'

export interface UseAppHotkeyOptions {
  /** `false` keeps the registration (visible in devtools) and only
   * suppresses firing — pass this instead of skipping the hook call. */
  enabled?: boolean
}

/** One keyboard shortcut, e.g. `"Mod+K"` or `"r"`. */
export function useAppHotkey(
  hotkey: RegisterableHotkey,
  callback: HotkeyCallback,
  options?: UseAppHotkeyOptions,
): void {
  useHotkey(hotkey, callback, options)
}

export type AppHotkeySequenceDefinition = UseHotkeySequenceDefinition

/**
 * A data-driven list of Vim-style sequences, e.g. `["G", "T"]` for `G T`.
 * One hook call registers the whole (possibly dynamic-length) list — see
 * NAV_HOTKEYS in `registry.ts` — rather than calling a singular hook in a
 * loop, which the rules of hooks don't allow.
 */
export function useAppHotkeySequences(definitions: AppHotkeySequenceDefinition[]): void {
  useHotkeySequences(definitions)
}
