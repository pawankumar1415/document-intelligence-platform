import { SlidersHorizontal, X } from "lucide-react";
import { useState } from "react";

import ModelControlBar from "./ModelControlBar";

const AIControlDrawer = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button className="ai-drawer-toggle" type="button" onClick={() => setOpen(true)}>
        <SlidersHorizontal size={16} /> AI Controls
      </button>

      {open && (
        <div className="ai-drawer-overlay" role="presentation" onClick={() => setOpen(false)}>
          <aside
            className="ai-drawer-panel"
            role="dialog"
            aria-label="AI Runtime Controls"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="ai-drawer-header">
              <h2>AI Runtime Controls</h2>
              <button className="ai-drawer-close" type="button" onClick={() => setOpen(false)}>
                <X size={18} />
              </button>
            </header>
            <div className="ai-drawer-content">
              <ModelControlBar />
            </div>
          </aside>
        </div>
      )}
    </>
  );
};

export default AIControlDrawer;
