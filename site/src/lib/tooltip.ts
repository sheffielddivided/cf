// One shared tooltip element, positioned next to the pointer or the focused mark.
let el: HTMLDivElement | null = null;

function ensure(): HTMLDivElement {
  if (!el) {
    el = document.createElement("div");
    el.className = "tip";
    el.setAttribute("role", "status");
    el.hidden = true;
    document.body.appendChild(el);
  }
  return el;
}

export function showTip(html: string, x: number, y: number): void {
  const tip = ensure();
  tip.innerHTML = html;
  tip.hidden = false;
  const r = tip.getBoundingClientRect();
  const left = Math.min(x + 14, window.innerWidth - r.width - 8);
  const top = y + 14 + r.height > window.innerHeight ? y - r.height - 10 : y + 14;
  tip.style.left = `${Math.max(8, left)}px`;
  tip.style.top = `${Math.max(8, top)}px`;
}

export function showTipAt(html: string, target: Element): void {
  const r = target.getBoundingClientRect();
  showTip(html, r.left + r.width / 2, r.top + r.height / 2);
}

export function hideTip(): void {
  if (el) el.hidden = true;
}

export const esc = (s: string) =>
  s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
