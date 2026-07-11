"use client";

type HeaderProps = {
  onMenuClick: () => void;
};

export function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-canvas/80 px-4 py-3 backdrop-blur md:px-8">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-lg border border-line px-3 py-1.5 text-sm text-ink-muted md:hidden"
          aria-label="Open navigation"
        >
          Menu
        </button>
        <p className="hidden text-sm text-ink-muted md:block">
          Control plane · localhost only
        </p>
      </div>
      <div className="rounded-full border border-line px-3 py-1 text-xs text-ink-faint">
        Offline-first
      </div>
    </header>
  );
}
