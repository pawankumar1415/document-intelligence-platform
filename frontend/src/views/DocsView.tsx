import {
  ArrowUpDown,
  BarChart2,
  BookMarked,
  BookOpen,
  ClipboardCheck,
  FileText,
  FolderOpen,
  Layers,
  LayoutDashboard,
  Library,
  MessageSquare,
  Settings,
  Table2,
  Wand2,
} from "lucide-react";

/* ── Types ───────────────────────────────────────────────────────────────── */

type TestCase = string;

interface DocSection {
  id: string;
  icon: React.ReactNode;
  title: string;
  group: string;
  tagline: string;
  description: string;
  testDoc: string | null;
  steps: string[];
  testCases: TestCase[];
  tips: string[];
}

/* ── Content ─────────────────────────────────────────────────────────────── */

const SECTIONS: DocSection[] = [
  {
    id: "studio",
    icon: <LayoutDashboard size={18} />,
    title: "Studio",
    group: "Workspace",
    tagline: "Upload documents and generate polished deliverables in one place.",
    description:
      "The Studio is the primary workspace. You upload a source document (requirements brief, RFP, SOW draft, case study notes) and the platform parses it, detects its use case, and lets you generate one or more output types: SOW, PowerPoint deck, Bid/Proposal, or Case Study. Each generation call sends the parsed text to your configured LLM and returns a structured, downloadable DOCX or PPTX.",
    testDoc: "02_Project_Brief_Data_Platform.txt → SOW / PPT\n01_RFP_Digital_Transformation.txt → Bid Response",
    steps: [
      "Navigate to Studio in the sidebar.",
      "Click the upload area or drag a file. Supported: .docx, .txt, .pdf, .xlsx, .xls, .csv, .jpg, .jpeg, .png, .webp, .bmp, .tiff.",
      "The platform parses the document and shows a summary with word count and extraction signals.",
      "Select a generation tab: SOW, PPT, Bid, or Case Study.",
      "Fill in the required fields (client name, project name, etc.) — most are pre-filled from the parsed document.",
      "Click Generate. The output downloads automatically and appears in Output Library.",
    ],
    testCases: [
      "Parsing a .txt file returns sections split on double newlines",
      "Parsing a .docx file maps Word heading styles to section headings",
      "Parsing a .pdf uses Docling with OCR and table structure",
      "Unsupported file types return a 400 error with the supported format list",
      "Use-case screening rejects non-project documents (e.g. a CV)",
      "SOW generation produces sections: Scope, Deliverables, Timeline, Assumptions, Pricing",
      "Bid generation produces sections: Executive Summary, Our Approach, Team, Pricing, Why Us",
      "PPT generation produces 6–12 content slides with a cover and closing slide",
    ],
    tips: [
      "If the use-case screening rejects your document, scroll down — you can override and generate anyway.",
      "The LLM provider selected in AI Settings applies to all generations. Switch to Groq for faster (but less detailed) output.",
      "Excel and CSV files are converted to markdown tables before generation — great for data-heavy scopes.",
      "Images are run through a vision model to extract text before any generation.",
    ],
  },
  {
    id: "chat",
    icon: <MessageSquare size={18} />,
    title: "Document Chat",
    group: "Workspace",
    tagline: "Ask questions about your uploaded documents using RAG.",
    description:
      "Document Chat lets you converse with your uploaded documents. Each question is classified by intent (document search vs. general). For document questions the platform embeds your query, retrieves the top-5 most relevant chunks from pgvector, and injects them as context into the LLM prompt along with the last 20 messages of conversation history. Sessions persist across the browser session — a new session is created automatically on first message and the ID is sent back on every follow-up.",
    testDoc: "05_Programme_Document_Rich.txt — upload it first via Studio, then ask questions in Chat.",
    steps: [
      "Upload one or more documents via Studio (they are automatically embedded and indexed).",
      "Navigate to Document Chat.",
      "Optionally select a Project from the top bar to scope retrieval to that project's documents.",
      "Type a question and press Enter or click Send.",
      "The session ID is maintained automatically — just keep asking follow-up questions.",
    ],
    testCases: [
      "First message creates a new session_id returned in the response",
      "Subsequent messages with the same session_id load the last 20 turns from SQLite",
      "Intent classifier routes document questions to vector search",
      "Intent classifier routes greetings / off-topic questions to general (no retrieval)",
      "Project-scoped queries only return chunks from that project's documents",
      "Cross-project search works when no project is selected",
      "Hallucination guard: model says 'I don't have enough information' when context is empty",
    ],
    tips: [
      "Sessions reset on page refresh — the session ID is held in React state only. Bookmark the URL if you need to return to a session.",
      "For best recall, upload the full document rather than a pasted excerpt.",
      "Ask follow-up questions naturally — the full conversation history is in the LLM prompt.",
      "Try: 'What are the critical risks?', 'Who is the most concerned stakeholder?', 'What decisions need to be made before 30 April?'",
    ],
  },
  {
    id: "outputs",
    icon: <Library size={18} />,
    title: "Output Library",
    group: "Workspace",
    tagline: "Browse, download, rate, and share every generated artifact.",
    description:
      "The Output Library is a persistent store of every artifact ever generated by the platform. Each artifact can be downloaded, rated (thumbs up/down per section), and shared via a public link with an optional expiry date. Share tokens are 32-character URL-safe strings. The public share page requires no authentication.",
    testDoc: "Generate at least one artifact via Studio first.",
    steps: [
      "Navigate to Output Library.",
      "Browse the list of artifacts grouped by type.",
      "Click Download to get the DOCX or PPTX file.",
      "Use the thumbs up/down buttons to rate individual sections — this feedback is stored for quality review.",
      "Click Share to create a public link. Set an expiry date or leave it permanent.",
      "Copy the share URL and send it to a stakeholder — no login required to view it.",
      "Click Revoke to invalidate a share link at any time.",
    ],
    testCases: [
      "Artifacts are isolated per user — other users cannot access your artifacts",
      "Share link token is at least 20 characters",
      "Expired share links return 404 on the public page",
      "Revoked share links return 404 immediately",
      "Feedback ratings (1 / -1) are saved per section_title per artifact",
      "Feedback is isolated per user",
    ],
    tips: [
      "Share links are fully public — anyone with the URL can view and download the artifact.",
      "Set an expiry if you are sharing with external stakeholders for a time-limited review.",
    ],
  },
  {
    id: "projects",
    icon: <FolderOpen size={18} />,
    title: "Projects",
    group: "Workspace",
    tagline: "Organise documents and artifacts into client engagement workspaces.",
    description:
      "Projects are named containers that group related documents, generated artifacts, validations, and clauses together. Every upload in Studio can be assigned to a project. The Project Detail page gives a tabbed overview of everything in the project — Documents, Artifacts, Validations, and Clauses. Chat scoping to a project limits vector search to that project's documents.",
    testDoc: "Create a project first, then upload any test document and assign it.",
    steps: [
      "Navigate to Projects and click New Project.",
      "Give the project a name (e.g. 'Meridian Housing RFP').",
      "Go back to Studio, upload a document, and select the project from the dropdown.",
      "Open the project from the Projects list to see the tabbed workspace.",
      "In Document Chat, select the project from the top bar to scope questions to it.",
    ],
    testCases: [
      "Project list is isolated per user — user A cannot see user B's projects",
      "Project overview aggregates documents, artifacts, and validations correctly",
      "Deleting a project is not yet supported (by design — data safety)",
    ],
    tips: [
      "Use one project per client engagement to keep context clean.",
      "The Project Overview page shows a live count of documents, artifacts, and validations.",
    ],
  },
  {
    id: "templates",
    icon: <Wand2 size={18} />,
    title: "Template Library",
    group: "Workspace",
    tagline: "Save and reuse custom generation configurations.",
    description:
      "Templates let you save a named configuration (tone, structure, custom instructions) for each generation type — SOW, PPT, Bid, or Case Study. Four default templates are seeded automatically for every user. Default templates cannot be deleted. Custom templates can be created and deleted freely.",
    testDoc: "No specific document needed — templates are configuration objects.",
    steps: [
      "Navigate to Templates.",
      "Use the type filter to browse templates by category.",
      "Click New Template, fill in the name, description, type, and any config JSON.",
      "Delete custom templates with the trash icon (default templates show a lock).",
    ],
    testCases: [
      "Default templates are seeded automatically (one per type: sow, pptx, bid, case_study)",
      "Default templates cannot be deleted (delete returns false)",
      "Custom templates are isolated per user",
      "Template list can be filtered by type",
      "get_template returns null for another user's template ID",
    ],
    tips: [
      "Template config is a free-form JSON object — use it to store tone preferences, section overrides, or client-specific instructions.",
    ],
  },
  {
    id: "compare",
    icon: <ArrowUpDown size={18} />,
    title: "Compare Docs",
    group: "Workspace",
    tagline: "Detect improvements and regressions between two document versions.",
    description:
      "The Compare Docs page performs a structured diff of two documents using the LLM. It produces an overall sentiment (improved / regressed / neutral), per-document scores, and a detailed change list categorised as added, removed, improved, regressed, or unchanged. Ideal for comparing SOW drafts, contract revisions, or RFP iterations.",
    testDoc: "03_SOW_v1_Original.txt (Doc A)  +  04_SOW_v2_Revised.txt (Doc B)",
    steps: [
      "Navigate to Compare Docs.",
      "Paste or upload Doc A (the baseline) on the left.",
      "Paste or upload Doc B (the revised version) on the right.",
      "Click Compare. Results appear below with scores and a change table.",
    ],
    testCases: [
      "v1 → v2 comparison returns sentiment = 'improved'",
      "Doc B score is higher than Doc A score",
      "Change list identifies: budget increase (£185k → £224k), new directorate, extended timeline",
      "Unchanged sections are still listed with change_type = 'unchanged'",
    ],
    tips: [
      "Works best with documents of similar structure.",
      "You can paste raw text or upload a .txt / .md file using the upload icon next to each panel.",
    ],
  },
  {
    id: "extract",
    icon: <Table2 size={18} />,
    title: "Extract Data",
    group: "Workspace",
    tagline: "Pull structured tables out of unstructured documents.",
    description:
      "The Structured Extractor runs a schema-guided LLM extraction over a document. You select a pre-defined schema (e.g. Risks & Mitigations, Action Items, Stakeholders) and the platform extracts every matching entity into a table, which is downloadable as a DOCX with an embedded table.",
    testDoc: "05_Programme_Document_Rich.txt — contains risks, actions, stakeholders, decisions, requirements.",
    steps: [
      "Navigate to Extract Data.",
      "Paste your document text or upload a file.",
      "Select a schema from the dropdown (or create a custom one in the schema manager).",
      "Click Extract. The results table appears with one row per entity.",
      "Click Download to get a DOCX with the table.",
    ],
    testCases: [
      "Risks & Mitigations schema extracts 10 risks from the programme document",
      "Action Items schema extracts 7 actions with owners and due dates",
      "Stakeholders schema extracts 6 stakeholders with influence ratings",
      "Decisions schema extracts 3 key decisions with deadlines",
      "Custom schemas with user-defined fields work correctly",
      "Extraction result is saved as an artifact",
    ],
    tips: [
      "Default schemas are seeded automatically — you can clone and modify them.",
      "For long documents, the extraction prompt is built from the full text — keep documents under ~20k words for reliable results.",
    ],
  },
  {
    id: "clauses",
    icon: <BookOpen size={18} />,
    title: "Clause Library",
    group: "Workspace",
    tagline: "Save, search, and auto-extract reusable contract clauses.",
    description:
      "The Clause Library stores reusable clauses extracted from your documents. You can add clauses manually, auto-extract them from a document using the LLM, tag them for easy retrieval, and search across all clauses with semantic or keyword search.",
    testDoc: "05_Programme_Document_Rich.txt — Section 7 (Governance Clauses) contains four reusable clauses.",
    steps: [
      "Navigate to Clause Library.",
      "Click Auto-Extract, paste document text (or use Section 7 of the programme doc), and run extraction.",
      "Review the extracted clauses and save the ones you want.",
      "Use the search bar to find clauses by keyword or tag.",
      "Click a clause to copy it into your clipboard.",
    ],
    testCases: [
      "Auto-extract identifies reporting/escalation, change control, QA, and confidentiality clauses from Section 7",
      "Manually created clauses are searchable immediately",
      "Clauses are isolated per user",
      "Clause tags filter correctly",
    ],
    tips: [
      "Tag clauses by document type (e.g. 'SOW', 'NDA') so you can quickly find the right one during generation.",
      "Auto-extract works best on legal or governance sections — not narrative prose.",
    ],
  },
  {
    id: "case-study",
    icon: <BookMarked size={18} />,
    title: "Case Studies",
    group: "Workspace",
    tagline: "Generate branded case study documents from engagement notes.",
    description:
      "The Case Study generator produces a structured, client-ready case study document. It takes engagement notes or a source document, client details, headline metrics, and our approach points — and generates a narrative case study with challenge, solution, and results sections.",
    testDoc: "BSBI_Platform_Case_Study.txt or BSBI_Platform_Case_Study.docx",
    steps: [
      "Navigate to Case Studies.",
      "Fill in the client name, industry, and engagement title.",
      "Upload or paste your source document / engagement notes.",
      "Add headline metrics (e.g. '40% reduction in processing time') and approach points.",
      "Click Generate. Download the resulting DOCX.",
    ],
    testCases: [
      "Case study generation produces sections: Background, Challenge, Our Approach, Results, Metrics",
      "Headline metrics appear as a metrics table in the output",
      "Output is saved as a case_study artifact in Output Library",
    ],
    tips: [
      "Headline metrics make the biggest impact — quantify outcomes wherever possible.",
      "The more detailed your approach points, the richer the generated narrative.",
    ],
  },
  {
    id: "validate",
    icon: <ClipboardCheck size={18} />,
    title: "Validate Document",
    group: "Validation",
    tagline: "Score a document against a quality rubric with two-layer analysis.",
    description:
      "Validation runs in two layers. Layer 1 checks rubric compliance — each criterion is assessed and a 0–100 compliance score is produced. Layer 2 checks internal consistency (contradictions, undefined terms, dangling references). The overall verdict is PASS, PASS_WITH_WARNINGS, or FAIL. A rewritten version of the text is also generated with issues addressed.",
    testDoc: "Paste the Governance Clauses from 05_Programme_Document_Rich.txt (Section 7), or any generated SOW/Bid.",
    steps: [
      "Navigate to Validate Document.",
      "Paste document text or upload a .txt / .md file.",
      "Select a rubric from the dropdown (the Default rubric is pre-selected).",
      "Click Validate. Compliance score, issues, and passed criteria appear.",
      "Scroll down to see the rewritten text with issues corrected.",
    ],
    testCases: [
      "Compliance score is between 0 and 100",
      "PASS verdict when score ≥ 70 with no high-severity issues",
      "FAIL verdict when score < 50 or a high-severity criterion fails",
      "Rewritten text is returned for FAIL and PASS_WITH_WARNINGS verdicts",
      "Layer 2 consistency issues are reported separately from Layer 1",
      "Custom rubrics with user-defined criteria are applied correctly",
    ],
    tips: [
      "The Default rubric covers: clarity, completeness, measurable outcomes, risk coverage, and timeline clarity.",
      "Create custom rubrics in the rubric manager for client-specific quality standards.",
      "Scores above 70% are considered a pass — below 55% is a hard fail.",
    ],
  },
  {
    id: "batch-validate",
    icon: <Layers size={18} />,
    title: "Batch Validation",
    group: "Validation",
    tagline: "Validate multiple documents at once and get a summary report.",
    description:
      "Batch Validation runs the same two-layer validation pipeline over multiple documents simultaneously. Upload an Excel or CSV file where each row is a document (name + text), or paste multiple documents. All results share the same rubric. A summary shows pass/fail counts and average score.",
    testDoc: "Create a small .xlsx with columns 'document_name' and 'text', containing 2–3 rows from different test docs.",
    steps: [
      "Navigate to Batch Validation.",
      "Upload an .xlsx / .csv file or manually add document rows.",
      "Select a rubric.",
      "Click Run Batch. Results appear in a table with individual scores and verdicts.",
    ],
    testCases: [
      "All items in the batch use the same rubric",
      "Each item returns an independent score and verdict",
      "Summary aggregates total, pass count, and average score",
      "A single failing item does not block the others from completing",
    ],
    tips: [
      "Batch validation is ideal for comparing outputs from different LLM providers side-by-side.",
    ],
  },
  {
    id: "analytics",
    icon: <BarChart2 size={18} />,
    title: "Analytics",
    group: "Insights",
    tagline: "Track quality trends, pass rates, and platform activity over time.",
    description:
      "The Analytics dashboard aggregates all platform activity for the logged-in user. It shows total documents, artifacts, validations, and clauses; average compliance score; pass rate; a validation trend chart; the most common issues flagged by the rubric; and a recent activity feed.",
    testDoc: "No specific document needed — analytics populate as you use other features.",
    steps: [
      "Use the platform normally across multiple features.",
      "Navigate to Analytics to see the dashboard populate.",
    ],
    testCases: [
      "Overview counters increment correctly after each upload / generation / validation",
      "Average compliance score recalculates after each validation",
      "Pass rate reflects proportion of PASS verdicts",
      "Validation trend shows one data point per day with activity",
      "Common issues list sorts by frequency descending",
    ],
    tips: [
      "Run a mix of high-quality and low-quality documents through validation to see trends diverge.",
    ],
  },
  {
    id: "settings",
    icon: <Settings size={18} />,
    title: "AI Settings",
    group: "Configuration",
    tagline: "Configure your LLM provider, model, and embedding backend.",
    description:
      "AI Settings controls which LLM provider and model is used for all generation, extraction, validation, and chat operations. Supported providers: OpenAI, Groq, Azure OpenAI, and Ollama (local). The embedding backend (used for RAG) can also be changed — supported options are OpenAI text-embedding-3 models and a local fallback.",
    testDoc: "No document needed — change settings and re-run any generation to compare output quality.",
    steps: [
      "Navigate to AI Settings.",
      "Select a provider from the dropdown.",
      "Select a model (the list updates based on the provider).",
      "Optionally change the embedding model (this affects all future document uploads — existing embeddings are not re-indexed).",
      "Settings are saved per session. Refresh the page to reset to defaults.",
    ],
    testCases: [
      "Provider catalog lists all configured providers with enabled/disabled status",
      "Model list updates correctly when provider changes",
      "Embedding model change is reflected in the vector status response",
      "Ollama provider is listed as disabled when OLLAMA_BASE_URL is not configured",
    ],
    tips: [
      "Groq with llama-3.3-70b-versatile is the fastest provider for generation tasks.",
      "OpenAI gpt-4o gives the highest quality output, especially for complex SOWs.",
      "Changing the embedding model does not re-embed existing documents — re-upload if you need consistency.",
    ],
  },
  {
    id: "file-formats",
    icon: <FileText size={18} />,
    title: "Supported File Formats",
    group: "Reference",
    tagline: "Everything the platform can parse and what it does with each format.",
    description:
      "The document parser supports seven format families. Each is converted to plain text + structured sections before being passed to the LLM. The parsed text is also chunked and embedded into pgvector for RAG chat.",
    testDoc: null,
    steps: [],
    testCases: [
      ".txt — split on double newlines into numbered sections",
      ".docx — Word heading styles map to section headings; paragraphs become section body",
      ".pdf — Docling with RapidOCR; exports to markdown preserving tables and layout",
      ".xlsx / .xls — each sheet becomes a section; rows rendered as a markdown table",
      ".csv — dialect auto-detected; rendered as a single markdown table",
      ".jpg / .jpeg / .png / .webp / .bmp / .tiff — sent to vision LLM with extraction prompt; response becomes the document text",
      "Unsupported extensions return HTTP 400 with the full supported format list",
    ],
    tips: [
      "For image parsing, make sure your configured LLM provider supports vision (OpenAI gpt-4o-mini, Groq llama-4-scout, Azure vision deployment, or a local llava model in Ollama).",
      "Large Excel files (>1000 rows per sheet) will produce very long prompts — consider trimming before upload.",
      "PDF parsing uses OCR by default. Set DOCLING_FORCE_FULL_PAGE_OCR=true in .env for scanned PDFs.",
    ],
  },
];

/* ── Page component ──────────────────────────────────────────────────────── */

const GROUP_ORDER = ["Workspace", "Validation", "Insights", "Configuration", "Reference"];

const DocsView = () => {
  const groups = GROUP_ORDER.map((g) => ({
    name: g,
    items: SECTIONS.filter((s) => s.group === g),
  })).filter((g) => g.items.length > 0);

  const scrollTo = (id: string) => {
    const el = document.getElementById(`doc-section-${id}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="docs-layout">
      {/* ── Left nav ── */}
      <aside className="docs-nav">
        <div className="docs-nav-title">Documentation</div>
        {groups.map((g) => (
          <div key={g.name} className="docs-nav-group">
            <span className="docs-nav-group-label">{g.name}</span>
            {g.items.map((s) => (
              <button
                key={s.id}
                className="docs-nav-item"
                onClick={() => scrollTo(s.id)}
                type="button"
              >
                {s.icon}
                {s.title}
              </button>
            ))}
          </div>
        ))}
      </aside>

      {/* ── Content ── */}
      <div className="docs-content">
        <div className="docs-header">
          <h1 className="docs-page-title">Platform Documentation</h1>
          <p className="docs-page-sub">
            Complete reference for every feature — how to use it, which test documents to use,
            and what test cases are covered.
          </p>
        </div>

        {groups.map((g) => (
          <div key={g.name} className="docs-group-block">
            <div className="docs-group-heading">{g.name}</div>
            {g.items.map((section) => (
              <section
                key={section.id}
                id={`doc-section-${section.id}`}
                className="docs-section-card"
              >
                {/* Section header */}
                <div className="docs-section-header">
                  <span className="docs-section-icon">{section.icon}</span>
                  <div>
                    <h2 className="docs-section-title">{section.title}</h2>
                    <p className="docs-section-tagline">{section.tagline}</p>
                  </div>
                </div>

                {/* Description */}
                <p className="docs-section-desc">{section.description}</p>

                <div className="docs-section-body">
                  {/* Test document */}
                  {section.testDoc && (
                    <div className="docs-block">
                      <div className="docs-block-label">Test Document</div>
                      <div className="docs-test-doc">
                        {section.testDoc.split("\n").map((line, i) => (
                          <span key={i} className="docs-test-doc-line">{line}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* How to use */}
                  {section.steps.length > 0 && (
                    <div className="docs-block">
                      <div className="docs-block-label">How to Use</div>
                      <ol className="docs-steps">
                        {section.steps.map((step, i) => (
                          <li key={i} className="docs-step">{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}

                  {/* Test cases */}
                  <div className="docs-block">
                    <div className="docs-block-label">Test Cases Covered</div>
                    <ul className="docs-test-cases">
                      {section.testCases.map((tc, i) => (
                        <li key={i} className="docs-test-case">
                          <span className="docs-test-case-dot" />
                          {tc}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Tips */}
                  {section.tips.length > 0 && (
                    <div className="docs-block docs-tips-block">
                      <div className="docs-block-label">Tips & Notes</div>
                      <ul className="docs-tips">
                        {section.tips.map((tip, i) => (
                          <li key={i} className="docs-tip">{tip}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DocsView;