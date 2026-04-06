import { ChevronRight, File, Folder, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { getSharePointFiles, getSharePointLibraries, getSharePointStatus } from "../services/api";
import type { SharePointFile, SharePointLibrary } from "../types/app";

type Props = {
  token: string | null;
  onSelect: (file: SharePointFile, libraryId: string) => void;
  acceptExtensions?: string[]; // e.g. [".docx", ".pdf", ".xlsx"]
  disabled?: boolean;
};

type PickerState = "checking" | "unconfigured" | "loading" | "ready" | "error";

const SUPPORTED_ICONS: Record<string, string> = {
  ".docx": "📄",
  ".doc": "📄",
  ".pdf": "📕",
  ".xlsx": "📊",
  ".xls": "📊",
  ".csv": "📋",
  ".txt": "📃",
};

function fileExt(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return iso.slice(0, 10);
  }
}

const SharePointPicker = ({ token, onSelect, acceptExtensions, disabled }: Props) => {
  const [state, setState] = useState<PickerState>("checking");
  const [errorMsg, setErrorMsg] = useState("");
  const [libraries, setLibraries] = useState<SharePointLibrary[]>([]);
  const [selectedLibrary, setSelectedLibrary] = useState<string>("");
  const [folderPath, setFolderPath] = useState("/");
  const [breadcrumbs, setBreadcrumbs] = useState<{ name: string; path: string }[]>([]);
  const [items, setItems] = useState<SharePointFile[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

  useEffect(() => {
    void checkStatus();
  }, [token]);

  useEffect(() => {
    if (state === "ready" && libraries.length > 0 && !selectedLibrary) {
      setSelectedLibrary(libraries[0].id);
    }
  }, [state, libraries]);

  useEffect(() => {
    if (selectedLibrary) {
      void loadFiles(selectedLibrary, "/");
    }
  }, [selectedLibrary]);

  const checkStatus = async () => {
    if (!token) return;
    setState("checking");
    try {
      const status = await getSharePointStatus({ token });
      if (!status.configured) {
        setState("unconfigured");
        return;
      }
      const libs = await getSharePointLibraries(null, { token });
      setLibraries(libs);
      setState("ready");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to connect to SharePoint.");
      setState("error");
    }
  };

  const loadFiles = async (libraryId: string, path: string) => {
    setLoadingFiles(true);
    setErrorMsg("");
    try {
      const result = await getSharePointFiles(libraryId, path, { token });
      setItems(result.items);
      setFolderPath(path);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load files.");
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleLibraryChange = (libId: string) => {
    setSelectedLibrary(libId);
    setBreadcrumbs([]);
    setFolderPath("/");
  };

  const handleFolderClick = (item: SharePointFile) => {
    const newPath = folderPath === "/" ? `/${item.name}` : `${folderPath}/${item.name}`;
    setBreadcrumbs((prev) => [...prev, { name: item.name, path: newPath }]);
    void loadFiles(selectedLibrary, newPath);
  };

  const handleBreadcrumb = (path: string, idx: number) => {
    setBreadcrumbs((prev) => prev.slice(0, idx));
    void loadFiles(selectedLibrary, path);
  };

  const handleRootClick = () => {
    setBreadcrumbs([]);
    void loadFiles(selectedLibrary, "/");
  };

  const isAccepted = (file: SharePointFile) => {
    if (!acceptExtensions || acceptExtensions.length === 0) return true;
    return acceptExtensions.includes(fileExt(file.name));
  };

  if (state === "checking") {
    return (
      <div className="sp-picker sp-picker-status">
        <Loader2 size={16} className="spin" />
        <span>Connecting to SharePoint…</span>
      </div>
    );
  }

  if (state === "unconfigured") {
    return (
      <div className="sp-picker sp-picker-status sp-picker-warn">
        <span>SharePoint is not configured. Add credentials to your <code>.env</code> file.</span>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="sp-picker sp-picker-status sp-picker-error">
        <span>{errorMsg}</span>
        <button type="button" className="sp-refresh-btn" onClick={() => void checkStatus()}>
          <RefreshCw size={13} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className={`sp-picker${disabled ? " sp-picker-disabled" : ""}`}>
      {/* Library selector */}
      <div className="sp-toolbar">
        <select
          className="form-control sp-library-select"
          value={selectedLibrary}
          onChange={(e) => handleLibraryChange(e.target.value)}
          disabled={disabled}
        >
          {libraries.map((lib) => (
            <option key={lib.id} value={lib.id}>
              {lib.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="sp-refresh-btn"
          onClick={() => void loadFiles(selectedLibrary, folderPath)}
          disabled={disabled || loadingFiles}
          title="Refresh"
        >
          <RefreshCw size={13} className={loadingFiles ? "spin" : ""} />
        </button>
      </div>

      {/* Breadcrumb */}
      <div className="sp-breadcrumb">
        <button type="button" className="sp-breadcrumb-item" onClick={handleRootClick} disabled={disabled}>
          Root
        </button>
        {breadcrumbs.map((crumb, idx) => (
          <span key={crumb.path} className="sp-breadcrumb-sep-row">
            <ChevronRight size={12} className="sp-breadcrumb-sep" />
            <button
              type="button"
              className="sp-breadcrumb-item"
              onClick={() => handleBreadcrumb(crumb.path, idx + 1)}
              disabled={disabled}
            >
              {crumb.name}
            </button>
          </span>
        ))}
      </div>

      {/* File list */}
      <div className="sp-file-list">
        {loadingFiles ? (
          <div className="sp-file-loading">
            <Loader2 size={14} className="spin" /> Loading…
          </div>
        ) : items.length === 0 ? (
          <div className="sp-file-empty">This folder is empty.</div>
        ) : (
          items.map((item) => {
            const accepted = !item.is_folder && isAccepted(item);
            const icon = item.is_folder ? null : (SUPPORTED_ICONS[fileExt(item.name)] ?? "📎");
            return (
              <button
                key={item.id}
                type="button"
                className={`sp-file-row${item.is_folder ? " sp-folder-row" : ""}${!item.is_folder && !accepted ? " sp-file-row-disabled" : ""}`}
                onClick={() => {
                  if (item.is_folder) handleFolderClick(item);
                  else if (accepted && !disabled) onSelect(item, selectedLibrary);
                }}
                disabled={disabled || (!item.is_folder && !accepted)}
                title={item.name}
              >
                <span className="sp-file-icon">
                  {item.is_folder ? <Folder size={14} /> : icon ? <span>{icon}</span> : <File size={14} />}
                </span>
                <span className="sp-file-name">{item.name}</span>
                {!item.is_folder && (
                  <>
                    <span className="sp-file-size">{formatBytes(item.size)}</span>
                    <span className="sp-file-date">{formatDate(item.last_modified)}</span>
                  </>
                )}
                {item.is_folder && <ChevronRight size={12} className="sp-folder-arrow" />}
              </button>
            );
          })
        )}
      </div>

      {errorMsg && <div className="sp-inline-error">{errorMsg}</div>}
    </div>
  );
};

export default SharePointPicker;