import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Copy,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useAppState } from "../context/AppStateContext";
import {
  autoExtractClauses,
  createClause,
  deleteClause,
  listClauses,
  searchClauses,
} from "../services/api";
import type { ClauseRecord } from "../types/app";

const TagBadge = ({ tag }: { tag: string }) => (
  <span style={{ background: "var(--surface-secondary)", borderRadius: 4, padding: "2px 7px", fontSize: 11, color: "var(--text-muted)", marginRight: 4 }}>{tag}</span>
);

const ClauseCard = ({ clause, onDelete, onCopy }: { clause: ClauseRecord; onDelete: (id: number) => void; onCopy: (text: string) => void }) => {
  const [expanded, setExpanded] = useState(false);
  const preview = clause.content.slice(0, 160);

  return (
    <div className="card" style={{ marginBottom: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{clause.title}</div>
          {clause.tags.length > 0 && (
            <div style={{ marginBottom: 6 }}>{clause.tags.map((t) => <TagBadge key={t} tag={t} />)}</div>
          )}
          <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0, lineHeight: 1.5 }}>
            {expanded ? clause.content : preview}{!expanded && clause.content.length > 160 && "…"}
          </p>
          {clause.content.length > 160 && (
            <button type="button" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--bsbi-red)", fontSize: 12, padding: 0, marginTop: 4 }} onClick={() => setExpanded((v) => !v)}>
              {expanded ? "Show less" : "Show more"}
            </button>
          )}
          {clause.source_doc && (
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>Source: {clause.source_doc}</div>
          )}
        </div>
        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
          <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: "4px 8px" }} onClick={() => onCopy(clause.content)}>
            <Copy size={12} /> Copy
          </button>
          <button type="button" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--status-fail)" }} onClick={() => onDelete(clause.id)}>
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};

const ClauseLibraryView = () => {
  const { token, llmProvider, llmModel } = useAppState();

  const [clauses, setClauses] = useState<ClauseRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ClauseRecord[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  // Add clause form
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newTags, setNewTags] = useState("");
  const [saving, setSaving] = useState(false);

  // Auto-extract
  const [showExtractForm, setShowExtractForm] = useState(false);
  const [extractDocName, setExtractDocName] = useState("");
  const [extractText, setExtractText] = useState("");
  const [extracting, setExtracting] = useState(false);

  const loadClauses = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listClauses({ token });
      setClauses(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load clauses.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadClauses(); }, [loadClauses]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const res = await searchClauses(searchQuery, { token });
      setSearchResults(res.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setSearchResults(null);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteClause(id, { token });
      setClauses((prev) => prev.filter((c) => c.id !== id));
      if (searchResults) setSearchResults((prev) => prev?.filter((c) => c.id !== id) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete clause.");
    }
  };

  const handleCopy = (text: string, id?: number) => {
    void navigator.clipboard.writeText(text).then(() => {
      if (id) { setCopied(id); setTimeout(() => setCopied(null), 2000); }
    });
  };

  const handleSaveClause = async () => {
    if (!newTitle.trim() || !newContent.trim()) return;
    setSaving(true);
    try {
      const record = await createClause(
        {
          title: newTitle.trim(),
          content: newContent.trim(),
          tags: newTags.split(",").map((t) => t.trim()).filter(Boolean),
          source_doc: "",
        },
        { token },
      );
      setClauses((prev) => [record, ...prev]);
      setShowAddForm(false);
      setNewTitle("");
      setNewContent("");
      setNewTags("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save clause.");
    } finally {
      setSaving(false);
    }
  };

  const handleAutoExtract = async () => {
    if (!extractText.trim() || !extractDocName.trim()) return;
    setExtracting(true);
    setError(null);
    try {
      const extracted = await autoExtractClauses(
        {
          document_name: extractDocName.trim(),
          text: extractText.trim(),
          llm_provider: llmProvider,
          llm_model: llmModel || null,
        },
        { token },
      );
      setClauses((prev) => [...extracted, ...prev]);
      setShowExtractForm(false);
      setExtractDocName("");
      setExtractText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auto-extraction failed.");
    } finally {
      setExtracting(false);
    }
  };

  const displayClauses = searchResults ?? clauses;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <BookOpen size={20} color="var(--bsbi-red)" style={{ marginRight: 8 }} />
          Clause Library
        </h1>
        <p className="page-subtitle">
          Save, search, and reuse professional text blocks from your best documents.
        </p>
      </div>

      {/* ── Search bar + actions ── */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200, display: "flex", gap: 6 }}>
          <input
            className="form-control"
            placeholder="Search clauses by keyword…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void handleSearch()}
          />
          <button type="button" className="btn btn-secondary" onClick={() => void handleSearch()} disabled={searching}>
            {searching ? <Loader2 size={14} className="spin" /> : <Search size={14} />}
          </button>
          {searchResults !== null && (
            <button type="button" className="btn btn-secondary" onClick={handleClearSearch}>Clear</button>
          )}
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => { setShowAddForm((v) => !v); setShowExtractForm(false); }}>
          <Plus size={13} /> Add Clause
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => { setShowExtractForm((v) => !v); setShowAddForm(false); }}>
          <Sparkles size={13} /> Auto-Extract from Doc
        </button>
      </div>

      {error && (
        <div className="message error" style={{ marginBottom: 12 }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* ── Add clause form ── */}
      {showAddForm && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 className="card-title">Add Clause Manually</h3>
          <label className="form-label">Title</label>
          <input className="form-control" style={{ marginBottom: 8 }} placeholder="e.g. Standard Governance Statement" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
          <label className="form-label">Content</label>
          <textarea className="form-control" rows={5} placeholder="Paste the reusable text…" value={newContent} onChange={(e) => setNewContent(e.target.value)} style={{ marginBottom: 8 }} />
          <label className="form-label">Tags (comma-separated)</label>
          <input className="form-control" style={{ marginBottom: 10 }} placeholder="e.g. governance, risk, scope" value={newTags} onChange={(e) => setNewTags(e.target.value)} />
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" className="btn btn-primary" onClick={() => void handleSaveClause()} disabled={saving || !newTitle.trim() || !newContent.trim()}>
              {saving ? <Loader2 size={13} className="spin" /> : <CheckCircle2 size={13} />} Save
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setShowAddForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      {/* ── Auto-extract form ── */}
      {showExtractForm && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 className="card-title">Auto-Extract Reusable Clauses</h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 10 }}>
            The AI will identify reusable paragraphs and save them to your library automatically.
          </p>
          <label className="form-label">Document Name</label>
          <input className="form-control" style={{ marginBottom: 8 }} placeholder="e.g. SOW v3 Final" value={extractDocName} onChange={(e) => setExtractDocName(e.target.value)} />
          <label className="form-label">Document Text</label>
          <textarea className="form-control" rows={8} placeholder="Paste document text…" value={extractText} onChange={(e) => setExtractText(e.target.value)} style={{ marginBottom: 10 }} />
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" className="btn btn-primary" onClick={() => void handleAutoExtract()} disabled={extracting || !extractText.trim() || !extractDocName.trim()}>
              {extracting ? <><Loader2 size={13} className="spin" /> Extracting…</> : <><Sparkles size={13} /> Extract Clauses</>}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setShowExtractForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      {/* ── Clause list ── */}
      {loading ? (
        <div className="validate-empty">
          <Loader2 size={36} className="spin" />
          <h2>Loading library…</h2>
        </div>
      ) : displayClauses.length === 0 ? (
        <div className="validate-empty">
          <BookOpen size={40} strokeWidth={1.2} />
          <h2>{searchResults !== null ? "No matching clauses" : "Library is empty"}</h2>
          <p>{searchResults !== null ? "Try a different search term." : "Add clauses manually or use Auto-Extract to populate your library."}</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {searchResults !== null && (
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 4 }}>
              {displayClauses.length} result{displayClauses.length !== 1 ? "s" : ""} for "{searchQuery}"
            </p>
          )}
          {displayClauses.map((clause) => (
            <div key={clause.id} style={{ position: "relative" }}>
              <ClauseCard
                clause={clause}
                onDelete={(id) => void handleDelete(id)}
                onCopy={(text) => handleCopy(text, clause.id)}
              />
              {copied === clause.id && (
                <div style={{ position: "absolute", top: 8, right: 48, background: "var(--status-pass)", color: "white", borderRadius: 4, padding: "3px 8px", fontSize: 11 }}>
                  Copied!
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ClauseLibraryView;