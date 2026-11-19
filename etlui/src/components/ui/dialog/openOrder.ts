import { ref, watch, type Ref } from 'vue'
import { injectDialogRootContext } from 'reka-ui'

// etlui: a portal's content sits where its Teleport was mounted, not where it was opened, so at an equal z-50 a dialog
// mounted later (a run's Steps) covers one opened later from it (a preview, a confirmation). Each dialog takes the
// next z-index when it opens instead. Used by DialogContent and AlertDialogContent (an AlertDialogRoot is a DialogRoot),
// and PopoverContent with its own `open` (a popover opened in a dialog, e.g. the cycle picker of Home).
let top = 50

export function useOpenOrderZIndex(open: Ref<boolean> = injectDialogRootContext().open) {
  const zIndex = ref(top)
  watch(open, isOpen => { if (isOpen) zIndex.value = ++top }, { immediate: true })
  return zIndex
}
