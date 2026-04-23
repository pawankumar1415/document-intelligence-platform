import { BookMarked, ChevronRight } from "lucide-react";
import { useState } from "react";

type Section = {
  id: string;
  title: string;
  content: React.ReactNode;
};

const sections: Section[] = [
  {
    id: "overview",
    title: "What is AI Narrative Search?",
    content: (
      <>
        <p>
          AI Narrative Search is a tool that reads text — called a <strong>narrative</strong> — and
          tells you how good it is. Think of it like a marking system: it checks whether your
          narrative is clear, complete, accurate, and professionally written, then gives it a score
          out of 10.
        </p>
        <p>
          It also compares your narrative against a library of approved examples (called
          reference narratives) and flags anything that looks unusual or out of place.
        </p>
        <p>
          Finally, if the narrative scores below a certain threshold, the AI can suggest an
          improved version that keeps all the facts but fixes the problems.
        </p>
        <div className="docs-callout">
          <strong>Who is this for?</strong> Anyone who needs to review, quality-check, or
          standardise large volumes of written text — project managers, analysts, bid writers,
          compliance teams, and reviewers.
        </div>
      </>
    ),
  },
  {
    id: "scoring",
    title: "How does scoring work?",
    content: (
      <>
        <p>
          Every narrative goes through two checks, one after the other. These are called
          <strong> Layer 1</strong> and <strong>Layer 2</strong>.
        </p>

        <div className="docs-step-block">
          <div className="docs-step-num">Layer 1</div>
          <div>
            <strong>Quality Check — Rubric Compliance</strong>
            <p>
              The AI reads your narrative and evaluates it against a scoring rubric — a list of
              criteria that a good narrative should meet. Each criterion is assessed and a score
              from 0 to 10 is produced.
            </p>
            <p>
              Any problems found are listed as <em>issues</em>. Each issue has a severity:
            </p>
            <ul>
              <li><strong>HIGH</strong> — deducts 2 points. Serious problems (e.g. unclear writing, missing critical information).</li>
              <li><strong>MEDIUM</strong> — deducts 1 point. Moderate problems (e.g. missing dates, vague language).</li>
              <li><strong>LOW</strong> — deducts 0.5 points. Minor concerns (e.g. informal tone, light jargon).</li>
            </ul>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">Layer 2</div>
          <div>
            <strong>Comparison Check — Reference Abnormality Detection</strong>
            <p>
              The AI searches your reference library for narratives that are similar to the one
              being scored. It then compares the two and looks for differences — things your
              narrative is missing, claiming differently, or structuring unusually.
            </p>
            <p>These differences are called <em>abnormalities</em> and come in five types:</p>
            <ul>
              <li><strong>Missing Information</strong> — something the reference narratives always include that yours does not.</li>
              <li><strong>Unusual Claim</strong> — a statement that contradicts what similar narratives say.</li>
              <li><strong>Data Discrepancy</strong> — a number or date that seems out of the normal range.</li>
              <li><strong>Structural</strong> — the narrative is organised differently from the reference examples.</li>
              <li><strong>Tone</strong> — the writing style is significantly different (e.g. informal where the references are formal).</li>
            </ul>
            <p>
              Layer 2 only runs if you have uploaded reference narratives. If no references are
              loaded, it is skipped automatically with a note.
            </p>
          </div>
        </div>

        <div className="docs-verdict-table">
          <div className="docs-verdict-row docs-verdict-pass">
            <span>Score 8 – 10</span><span className="verdict-badge verdict-pass">PASS</span>
          </div>
          <div className="docs-verdict-row docs-verdict-warn">
            <span>Score 6 – 7</span><span className="verdict-badge verdict-warn">PASS WITH WARNINGS</span>
          </div>
          <div className="docs-verdict-row docs-verdict-fail">
            <span>Score below 6</span><span className="verdict-badge verdict-fail">FAIL</span>
          </div>
        </div>
      </>
    ),
  },
  {
    id: "single",
    title: "Scoring a single narrative",
    content: (
      <>
        <p>
          Go to <strong>Score Narrative</strong> in the left sidebar. You will see a form on the
          left and a results panel on the right.
        </p>

        <div className="docs-step-block">
          <div className="docs-step-num">1</div>
          <div>
            <strong>Enter a Unique ID</strong>
            <p>
              This is a code that identifies the piece of work the narrative belongs to — for
              example, a project number, a reference code, or a case ID. Examples:
              <code>PROJ-001</code>, <code>P07|Security Systems</code>, <code>NDA-2024-003</code>.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">2</div>
          <div>
            <strong>Provide the narrative text</strong>
            <p>You have three ways to provide the text:</p>
            <ul>
              <li><strong>Paste Text</strong> — type or paste the narrative directly into the text box.</li>
              <li>
                <strong>Local File</strong> — upload a document from your computer. Accepted formats
                are <code>.txt</code>, <code>.docx</code> (Word), <code>.pdf</code>, and spreadsheets
                (<code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>). For spreadsheets, the system
                parses every row and shows a <em>Select Project</em> dropdown — choose the row you want
                to score and its narrative populates automatically. You can edit the text directly in
                the preview box before scoring.
              </li>
              <li>
                <strong>SharePoint</strong> — browse your organisation's SharePoint library and select
                a file. Plain documents (<code>.txt</code>, <code>.docx</code>, <code>.pdf</code>) are
                extracted as text. Spreadsheets (<code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>)
                show the same project-selection dropdown. (SharePoint must be configured by your administrator.)
              </li>
            </ul>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">3</div>
          <div>
            <strong>Select a Rubric</strong>
            <p>
              A rubric is the set of criteria the AI uses to score the narrative. The Default
              Narrative Rubric covers seven general criteria: Clarity, Completeness, Accuracy,
              Structure, Professional Tone, No Jargon, and Consistent Dates. Your administrator
              may have created additional rubrics for specific types of work.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">4</div>
          <div>
            <strong>Click Run AI Score</strong>
            <p>
              The AI analyses the narrative — this usually takes 5 to 20 seconds. Results appear
              on the right: the verdict (PASS / WARN / FAIL), a score out of 10, a list of
              quality issues, any abnormalities found against your reference library, and an
              AI-suggested rewrite if the score is below 8.
            </p>
          </div>
        </div>

        <div className="docs-callout docs-callout-tip">
          <strong>Tip:</strong> If the AI suggests a rewrite and you agree with it, click
          "Use This Rewrite" — the text is placed back into the text box so you can edit
          and re-score it immediately.
        </div>
        <div className="docs-callout">
          <strong>State is preserved between tabs.</strong> Navigating to Analytics, Settings,
          or any other page and coming back will not clear your uploaded file, selected project,
          or scoring results. Your work stays intact until you explicitly reset it or upload a
          different file.
        </div>
      </>
    ),
  },
  {
    id: "batch",
    title: "Batch scoring (multiple narratives)",
    content: (
      <>
        <p>
          Go to <strong>Batch Score</strong> in the sidebar. Instead of entering one narrative at
          a time, you upload a spreadsheet that contains many narratives and the system scores all
          of them.
        </p>

        <div className="docs-step-block">
          <div className="docs-step-num">1</div>
          <div>
            <strong>Upload your file</strong>
            <p>
              Click the upload area and select an Excel file (<code>.xlsx</code> or <code>.xls</code>)
              or a CSV file (<code>.csv</code>). The file should have one row per narrative.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">2</div>
          <div>
            <strong>Confirm the column mapping</strong>
            <p>
              After uploading, the system analyses your file's columns and suggests which column
              contains the unique ID and which contains the narrative text. It does this by
              examining the column names and the actual content of the cells.
            </p>
            <p>
              You will see the suggested columns with sample values shown beneath each dropdown.
              Review these and change them if the suggestion is wrong — simply select the correct
              column from the dropdown.
            </p>
            <p>
              If you are not sure and want a second opinion, click <strong>AI Detection</strong>.
              This sends the column names and a few sample rows to the AI, which makes a more
              intelligent guess based on the actual data rather than just the column name.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">3</div>
          <div>
            <strong>Choose scoring options and run</strong>
            <p>
              Select a rubric, set the reference depth (how many reference examples to compare
              each narrative against), and click <strong>Run Batch Score</strong>. Each row is
              scored independently. The results table shows each narrative's verdict, score, and
              issue count. Click any row to expand it and see the full detail.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">4</div>
          <div>
            <strong>Export the results</strong>
            <p>
              Click <strong>Export CSV</strong> to download a spreadsheet containing all results,
              including issues and abnormalities, ready for reporting or further analysis.
            </p>
          </div>
        </div>

        <div className="docs-callout">
          <strong>File format requirements:</strong> Your spreadsheet must have at least one
          column that acts as a unique identifier (e.g. a project code or reference number) and
          one column that contains the narrative text. Column names do not need to follow any
          specific convention — the system detects them automatically. After scoring, click
          <strong> Export CSV</strong> to download a spreadsheet with all results including
          the full AI-suggested rewrite text for each narrative.
        </div>
      </>
    ),
  },
  {
    id: "references",
    title: "Reference Library",
    content: (
      <>
        <p>
          The Reference Library stores your organisation's approved, high-quality narratives.
          These are used during Layer 2 scoring to find examples that are similar to the
          narrative being scored, so the AI can identify what is different or unusual.
        </p>
        <p>
          Think of it as giving the AI a set of "gold standard" examples to compare against. The
          more relevant examples you upload, the more accurate the abnormality detection becomes.
        </p>

        <div className="docs-step-block">
          <div className="docs-step-num">1</div>
          <div>
            <strong>Prepare your reference file</strong>
            <p>
              Create an Excel or CSV file where each row is one approved narrative. The file
              needs at least an ID column and a narrative text column. Any additional columns
              (such as project type, region, or period) are also stored and help improve
              similarity matching.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">2</div>
          <div>
            <strong>Upload the file</strong>
            <p>
              Go to <strong>Reference Library</strong> in the sidebar. Click the upload area on
              the left, select your file, add an optional description (e.g. "NDA P07 approved
              narratives"), and click <strong>Index Reference File</strong>.
            </p>
            <p>
              The system reads every row, converts the text into a mathematical representation
              (called an embedding), and stores it in a searchable database. This process is called
              indexing and may take a moment for large files.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">3</div>
          <div>
            <strong>Managing your library</strong>
            <p>
              You can upload multiple reference files — for example, one per project type or
              reporting period. Each file is listed on the right with its record count. To remove
              a file, click the red delete button next to it. This also removes all of its
              embeddings from the database.
            </p>
          </div>
        </div>

        <div className="docs-callout">
          <strong>No references yet?</strong> Layer 1 (rubric compliance scoring) works fully
          without any reference files — your narratives will still be scored out of 10 against
          the rubric criteria. Layer 2 (abnormality detection against similar examples) is
          skipped until at least one reference file is uploaded. The Reference Library page
          shows the default rubric criteria so you know what "gold standard" narratives should
          look like before you upload them.
        </div>
        <div className="docs-callout docs-callout-warn">
          <strong>Important:</strong> If you change the embedding model in Settings, you must
          re-upload all reference files. The old embeddings are stored at a different dimension
          and will not work with the new model.
        </div>
      </>
    ),
  },
  {
    id: "rubrics",
    title: "Rubrics (scoring criteria)",
    content: (
      <>
        <p>
          A rubric defines what makes a good narrative. It is a list of criteria that the AI
          checks, such as clarity, completeness, or accuracy.
        </p>
        <p>
          The system comes with a <strong>Default Narrative Rubric</strong> that covers seven
          general criteria suitable for most business writing. Administrators can create
          additional rubrics for specific use cases — for example, a rubric tuned for project
          status reports, bid narratives, or compliance statements.
        </p>
        <p>
          When scoring, you select which rubric to use. You can change the rubric between runs
          without affecting previously scored results.
        </p>
        <div className="docs-callout docs-callout-tip">
          <strong>Tip for administrators:</strong> Good rubric criteria are specific and
          measurable. Instead of "the narrative is good", write "the narrative includes a
          clear statement of the current status and any risks to delivery". The more precise
          the criterion, the more accurate the scoring.
        </div>
      </>
    ),
  },
  {
    id: "analytics",
    title: "Analytics",
    content: (
      <>
        <p>
          The <strong>Analytics</strong> page gives you a summary of all scoring activity in your
          account.
        </p>
        <ul>
          <li><strong>Total Scored</strong> — how many narratives you have scored in total.</li>
          <li><strong>Pass / Warnings / Fail counts</strong> — how your scores break down by verdict.</li>
          <li><strong>Average Score</strong> — the mean compliance score across all your runs.</li>
          <li><strong>Reference Files</strong> — how many reference files are in your library.</li>
          <li><strong>Pass Rate Bar</strong> — a visual split showing the proportion of each verdict.</li>
          <li><strong>Recent Scores</strong> — a table of the last 20 scoring runs with dates and results.</li>
        </ul>
        <p>
          Analytics are per-account — you only see your own scoring history. Administrators can
          see all users via the Admin Panel.
        </p>
      </>
    ),
  },
  {
    id: "settings",
    title: "Settings",
    content: (
      <>
        <p>
          The <strong>Settings</strong> page lets you configure the AI provider and the
          embedding model.
        </p>

        <h4 style={{ marginBottom: 8, marginTop: 16 }}>LLM Provider</h4>
        <p>
          The LLM (Large Language Model) is the AI that reads and scores narratives. You can
          switch between four providers:
        </p>
        <ul>
          <li><strong>OpenAI</strong> — GPT-4o, GPT-4o Mini. Requires an OpenAI API key.</li>
          <li><strong>Groq</strong> — Very fast inference. Requires a Groq API key.</li>
          <li><strong>Azure OpenAI</strong> — For organisations using Azure. Requires Azure credentials.</li>
          <li><strong>Ollama</strong> — Runs models locally on your own hardware. No API key required. Good for private deployments.</li>
        </ul>
        <p>
          Your API keys are set in the backend <code>.env</code> file by your administrator.
          You can switch between providers that have been configured without a restart.
        </p>

        <h4 style={{ marginBottom: 8, marginTop: 16 }}>Embedding Model</h4>
        <p>
          The embedding model converts text into numbers so that similarity comparisons can be
          made. It is used when indexing reference narratives and when retrieving similar examples
          during scoring. The default model is <code>nomic-ai/nomic-embed-text-v1.5</code> running
          locally — no internet connection is required.
        </p>
        <div className="docs-callout docs-callout-warn">
          <strong>Warning:</strong> Changing the embedding model requires you to re-upload all
          reference files. The old embeddings are incompatible with a different model.
        </div>
      </>
    ),
  },
  {
    id: "faq",
    title: "Common questions",
    content: (
      <>
        <div className="docs-faq-item">
          <div className="docs-faq-q">Why is the score lower than I expected?</div>
          <div className="docs-faq-a">
            Check the "Quality Issues" section — each issue shows what was deducted and why.
            HIGH issues deduct 2 points each, so even one or two serious problems can bring the
            score down significantly. Try fixing the issues listed and re-scoring.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">No abnormalities are showing even though I have reference files.</div>
          <div className="docs-faq-a">
            Check that the vector store (PostgreSQL + pgvector) is connected — if Layer 2 says
            "vector store not configured", ask your administrator to set up the database connection.
            Also make sure you have actually indexed at least one reference file in the Reference
            Library page.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">My Excel file is not being parsed correctly.</div>
          <div className="docs-faq-a">
            Go to Batch Score, upload the file, and check the column mapping panel. The system
            will show you which columns it detected for the ID and narrative. Use the dropdowns
            to select the correct columns if the automatic detection is wrong. You can also try
            "AI Detection" for a smarter guess based on the actual cell values.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">What file types can I upload?</div>
          <div className="docs-faq-a">
            <strong>Single scoring (Local File or SharePoint):</strong> <code>.txt</code>, <code>.docx</code>, <code>.pdf</code>,
            and spreadsheets (<code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>). Spreadsheets
            show a project-selection dropdown so you can score one row at a time.<br />
            <strong>Batch scoring:</strong> <code>.xlsx</code>, <code>.xls</code>, <code>.csv</code> — scores every row independently.<br />
            <strong>Reference Library:</strong> <code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">Ollama scoring fails with a 404 error.</div>
          <div className="docs-faq-a">
            This means the model requested is not installed in your local Ollama. Run{" "}
            <code>ollama list</code> to see what is available, then select a matching model in
            the LLM dropdown. For this deployment the available chat models are{" "}
            <code>qwen3.5:0.8b</code>, <code>llama3.2:3b</code>, and <code>qwen3:4b</code>.
            Make sure <code>ollama serve</code> is running before scoring.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">Can multiple people use the same account?</div>
          <div className="docs-faq-a">
            Each person should have their own account — analytics and scoring history are stored
            per user. Administrators can create and manage accounts from the Admin Panel.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">How long does scoring take?</div>
          <div className="docs-faq-a">
            A single narrative typically takes 5–20 seconds depending on the LLM provider and
            narrative length. Batch jobs depend on the number of rows — expect roughly 10–15
            seconds per row. Groq is the fastest provider if speed is a priority.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">My score seems inconsistent between runs.</div>
          <div className="docs-faq-a">
            AI models have some variability in their responses. Scores can vary by ±0.5 points
            between runs of the same text. This is normal. If you need reproducible scoring,
            consider using a more deterministic model configuration or averaging scores over
            multiple runs.
          </div>
        </div>
      </>
    ),
  },
];

export default function DocsView() {
  const [activeId, setActiveId] = useState("overview");
  const active = sections.find((s) => s.id === activeId) ?? sections[0];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <BookMarked size={20} color="var(--bsbi-red)" /> Documentation
        </h1>
        <p className="page-subtitle">
          Everything you need to know about using AI Narrative Search.
        </p>
      </div>

      <div className="docs-layout">
        {/* Sidebar nav */}
        <nav className="docs-nav">
          {sections.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`docs-nav-item${s.id === activeId ? " active" : ""}`}
              onClick={() => setActiveId(s.id)}
            >
              {s.id === activeId && <ChevronRight size={12} />}
              {s.title}
            </button>
          ))}
        </nav>

        {/* Content */}
        <article className="docs-content">
          <h2 className="docs-section-title">{active.title}</h2>
          <div className="docs-body">{active.content}</div>
        </article>
      </div>
    </div>
  );
}