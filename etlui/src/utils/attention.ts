/**
 * Brings the element of `selector` into view and, when `blink`, makes the button to click blink orange (`data-attention`,
 * base.css): the element itself if it is a button, else its first enabled button, else the element.
 * Used by the Forecast page's breadcrumb ("go to the current item").
 *
 * ponytail: waits for the element at most `frames` animation frames (a dialog's content renders a little after it
 * opens); a MutationObserver if a target ever takes longer.
 */
export function pointTo(selector: string, blink: boolean, frames = 20): void {
  const el = document.querySelector<HTMLElement>(selector)
  if (!el) {
    if (frames > 0) requestAnimationFrame(() => pointTo(selector, blink, frames - 1))
    return
  }
  el.scrollIntoView?.({ block: 'center', behavior: 'smooth' }) // not in happy-dom
  if (!blink) return
  const target = el.matches('button') ? el : (el.querySelector<HTMLElement>('button:not(:disabled)') ?? el)
  target.setAttribute('data-attention', '')
  setTimeout(() => target.removeAttribute('data-attention'), 2400) // the 3 blinks of base.css
}
