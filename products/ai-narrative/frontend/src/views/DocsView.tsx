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
          If you have uploaded financial reference data, it also cross-checks the monetary and
          schedule claims in the narrative against your data — this is called the financial
          accuracy check.
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
          Every narrative goes through up to three checks. These are called
          <strong> Layer 1</strong>, <strong>Layer 2</strong>, and <strong>Layer 3</strong>.
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
            <p>
              By default, the system uses the Default Narrative Rubric. If you have uploaded a
              compliance rules document via <strong>Standards</strong>, that is used instead.
            </p>
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

        <div className="docs-step-block">
          <div className="docs-step-num">Layer 3</div>
          <div>
            <strong>Financial Accuracy Check</strong>
            <p>
              Layer 3 is only active when you have uploaded financial reference data via{" "}
              <strong>Standards → Financial Reference Data</strong>. When active, the AI
              cross-references monetary and schedule claims in the narrative against the values in
              your data file.
            </p>
            <p>Discrepancies it looks for include:</p>
            <ul>
              <li><strong>Cost Overrun</strong> — narrative claims costs on target but data shows overspend.</li>
              <li><strong>Cost Underrun</strong> — narrative claims overspend but data shows underspend.</li>
              <li><strong>Schedule Slip</strong> — narrative's schedule claim contradicts the data value.</li>
              <li><strong>Data Conflict</strong> — a direct numerical contradiction between the narrative and the data.</li>
              <li><strong>Missing Reference</strong> — a financial record exists but the narrative makes no mention of it.</li>
            </ul>
            <p>
              Layer 3 matches on the <strong>Unique ID</strong> you provide. If no matching
              financial record is found for that ID, Layer 3 is skipped for that narrative
              (this is not treated as an error).
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
              <code>PROJ-001</code>, <code>P07|Security Systems</code>, <code>REF-2024-003</code>.
            </p>
            <p>
              If you have uploaded financial data, this ID is used to look up the matching record.
              Make sure the ID you enter here matches the ID column in your financial data file.
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
                to score and its narrative populates automatically.
              </li>
              <li>
                <strong>SharePoint</strong> — browse your organisation's SharePoint library and select
                a file. (SharePoint must be configured by your administrator.)
              </li>
            </ul>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">3</div>
          <div>
            <strong>Select a Rubric</strong>
            <p>
              A rubric is the set of criteria the AI uses to score the narrative. If you have
              uploaded a compliance rules document via <strong>Standards</strong>, those rules are
              used automatically — you do not need to select anything. Otherwise, the Default
              Narrative Rubric is used (seven general criteria: Clarity, Completeness, Accuracy,
              Structure, Professional Tone, No Jargon, Consistent Dates).
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">4</div>
          <div>
            <strong>Click Run AI Score</strong>
            <p>
              The AI analyses the narrative — this usually takes 5 to 20 seconds. Results appear
              on the right: the verdict (PASS / WARN / FAIL), a score out of 10, quality issues,
              any abnormalities from Layer 2, any financial discrepancies from Layer 3 (if active),
              and an AI-suggested rewrite if the score is below 8.
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
          or scoring results.
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
              Click the upload area and select an Excel file (<code>.xlsx</code> or <code>.xls</code>),
              a CSV file (<code>.csv</code>), a Word document (<code>.docx</code>), or a PDF (<code>.pdf</code>).
              The file should have one row per narrative for spreadsheets.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">2</div>
          <div>
            <strong>Confirm the column mapping</strong>
            <p>
              After uploading, the system analyses your file's columns and suggests which column
              contains the unique ID and which contains the narrative text.
            </p>
            <p>
              Review the suggested columns with sample values shown beneath each dropdown. Change
              them if the suggestion is wrong. If you are not sure, click{" "}
              <strong>AI Detection</strong> — this sends the column names and a few sample rows
              to the AI for a smarter guess.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">3</div>
          <div>
            <strong>Choose scoring options and run</strong>
            <p>
              Select a rubric, set the reference depth, and click <strong>Run Batch Score</strong>.
              Each row is scored independently, including Layer 3 if financial data is uploaded
              and the unique ID matches. The results table shows each narrative's verdict, score,
              and issue count. Click any row to expand it and see the full detail.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">4</div>
          <div>
            <strong>Export the results</strong>
            <p>
              Click <strong>Export CSV</strong> to download a spreadsheet containing all results,
              including issues, abnormalities, and financial discrepancies, ready for reporting
              or further analysis.
            </p>
          </div>
        </div>

        <div className="docs-callout">
          <strong>File format requirements:</strong> Your spreadsheet must have at least one
          column that acts as a unique identifier and one column that contains the narrative text.
          Column names do not need to follow any specific convention — the system detects them
          automatically.
        </div>
      </>
    ),
  },
  {
    id: "standards",
    title: "Standards — Rules & Financial Data",
    content: (
      <>
        <p>
          The <strong>Standards</strong> page lets you upload two types of data that modify how
          the scoring engine works. Access it from the left sidebar under DATA.
        </p>

        <div className="docs-step-block">
          <div className="docs-step-num">Rules</div>
          <div>
            <strong>Compliance Rules Document</strong>
            <p>
              Upload a document containing your organisation's narrative standards — this can be
              a Word document (<code>.docx</code>), PDF (<code>.pdf</code>), Excel
              (<code>.xlsx</code>), or CSV. The AI reads the document and extracts a list of
              scoring criteria with name, description, and severity.
            </p>
            <p>
              Once uploaded, these criteria become the active rubric for all scoring. The default
              rubric is no longer used until you remove the rules document. The Standards page
              shows the extracted criteria count and the source filename so you can confirm the
              right document was processed.
            </p>
            <p>
              To revert to the default rubric, click <strong>Remove rules — revert to default rubric</strong>.
            </p>
            <div className="docs-callout docs-callout-tip">
              <strong>Tip:</strong> Structure your rules document clearly — numbered or bulleted
              lists with a criterion name followed by a description work best. The AI is more
              accurate when criteria are specific rather than vague.
            </div>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">Financial</div>
          <div>
            <strong>Financial Reference Data</strong>
            <p>
              Upload an Excel or CSV file containing monetary and schedule data per project. The
              file must include a column whose values match the <strong>Unique ID</strong> values
              you use when scoring narratives. Extra columns (budget, spend, schedule dates, etc.)
              are all stored and made available to the Layer 3 financial accuracy check.
            </p>
            <p>
              Once uploaded, Layer 3 activates automatically. Every score run checks whether the
              narrative's unique ID has a matching row in your financial data, and if so, compares
              the narrative's financial and schedule claims against the data values.
            </p>
            <p>
              To deactivate Layer 3, click <strong>Remove financial data — disable Layer 3</strong>.
            </p>
            <div className="docs-callout docs-callout-warn">
              <strong>ID matching:</strong> The lookup is exact first, then case-insensitive. Make
              sure the ID format in your financial file (e.g. <code>PROJ-001</code>) matches the
              IDs you enter when scoring. Partial matches are not supported.
            </div>
          </div>
        </div>

        <h4 style={{ margin: "20px 0 8px" }}>How scoring layers are affected</h4>
        <ul>
          <li><strong>Layer 1</strong> — always runs. Uses your custom rules when uploaded, otherwise the default rubric.</li>
          <li><strong>Layer 2</strong> — runs when reference narratives are indexed in the Reference Library.</li>
          <li><strong>Layer 3</strong> — runs only when financial data is uploaded AND the narrative's unique ID is found in the data.</li>
        </ul>
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

        <div className="docs-step-block">
          <div className="docs-step-num">1</div>
          <div>
            <strong>Prepare your reference file</strong>
            <p>
              Create an Excel or CSV file where each row is one approved narrative. The file
              needs at least an ID column and a narrative text column. Any additional columns
              are also stored and help improve similarity matching.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">2</div>
          <div>
            <strong>Upload the file</strong>
            <p>
              Go to <strong>Reference Library</strong> in the sidebar. Click the upload area,
              select your file, add an optional description, and click{" "}
              <strong>Index Reference File</strong>.
            </p>
            <p>
              The system reads every row, converts the text into a mathematical representation
              (called an embedding), and stores it in a searchable database. This may take a
              moment for large files.
            </p>
          </div>
        </div>

        <div className="docs-step-block">
          <div className="docs-step-num">3</div>
          <div>
            <strong>Managing your library</strong>
            <p>
              You can upload multiple reference files — for example, one per project type or
              reporting period. Each file is listed with its record count. To remove a file,
              click the red delete button next to it.
            </p>
          </div>
        </div>

        <div className="docs-callout">
          <strong>No references yet?</strong> Layer 1 scoring works fully without any reference
          files. Layer 2 is skipped until at least one reference file is uploaded.
        </div>
        <div className="docs-callout docs-callout-warn">
          <strong>Important:</strong> If you change the embedding model in Settings, you must
          re-upload all reference files. The old embeddings are incompatible with a different model.
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
          additional rubrics for specific use cases.
        </p>
        <p>
          Rubric selection priority when scoring:
        </p>
        <ol>
          <li>If you explicitly select a rubric in the scoring form, that rubric is used.</li>
          <li>If you have uploaded a compliance rules document via <strong>Standards</strong>, those extracted criteria are used.</li>
          <li>Otherwise, the Default Narrative Rubric is used.</li>
        </ol>
        <div className="docs-callout docs-callout-tip">
          <strong>Tip for administrators:</strong> Good rubric criteria are specific and
          measurable. Instead of "the narrative is good", write "the narrative includes a
          clear statement of the current status and any risks to delivery".
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
          The <strong>Analytics</strong> page has two tabs: <strong>Overview</strong> and{" "}
          <strong>AI Performance Drift</strong>.
        </p>

        <h4 style={{ margin: "16px 0 8px" }}>Overview</h4>
        <ul>
          <li><strong>Total Scored</strong> — how many narratives you have scored in total.</li>
          <li><strong>Pass / Warnings / Fail counts</strong> — how your scores break down by verdict.</li>
          <li><strong>Average Score</strong> — the mean compliance score across all your runs.</li>
          <li><strong>Reference Files</strong> — how many reference files are in your library.</li>
          <li><strong>Pass Rate Bar</strong> — a visual split showing the proportion of each verdict.</li>
          <li><strong>Recent Scores</strong> — a table of the last 20 scoring runs with dates and results.</li>
        </ul>

        <h4 style={{ margin: "16px 0 8px" }}>AI Performance Drift</h4>
        <p>
          This tab tracks how scoring behaviour changes over time. It is useful for detecting
          model drift (gradual score changes that are not explained by content differences),
          provider or model switches, and the effect of prompt updates.
        </p>
        <ul>
          <li><strong>Daily Average Score chart</strong> — a line chart of the mean compliance score for each day in the last 30 days. Dashed vertical lines mark days where the AI provider changed.</li>
          <li><strong>Trend direction</strong> — whether scores are improving, declining, or stable based on linear regression over the 30-day window.</li>
          <li><strong>Score Variance</strong> — the standard deviation of daily average scores. High variance suggests inconsistent scoring.</li>
          <li><strong>Daily Verdict Distribution</strong> — a stacked bar per day showing the split of PASS / WARN / FAIL verdicts.</li>
          <li><strong>Model Distribution</strong> — how many scores were run with each model ID.</li>
          <li><strong>Provider Changes</strong> — a list of days where the primary provider switched.</li>
          <li><strong>Custom Rules Usage %</strong> — what percentage of runs used an uploaded compliance rules document.</li>
          <li><strong>Financial Check Usage %</strong> — what percentage of runs had Layer 3 active.</li>
        </ul>
        <p>
          Click <strong>Export CSV</strong> on the drift tab to download a full audit log
          of every score run in the 30-day window, suitable for archiving or importing
          into Excel.
        </p>

        <div className="docs-callout">
          Analytics are per-account — you only see your own scoring history. Administrators
          can see all users via the Admin Panel.
        </div>
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
          <li><strong>Ollama (default)</strong> — Runs models locally on your own hardware. No API key required. Good for private deployments.</li>
          <li><strong>OpenAI</strong> — GPT-4o, GPT-4o Mini. Requires an OpenAI API key.</li>
          <li><strong>Groq</strong> — Very fast inference. Requires a Groq API key.</li>
          <li><strong>Azure OpenAI</strong> — For organisations using Azure. Requires Azure credentials.</li>
        </ul>
        <p>
          Your API keys are set in the backend <code>.env</code> file by your administrator.
          You can switch between providers that have been configured without a restart.
        </p>

        <h4 style={{ marginBottom: 8, marginTop: 16 }}>Embedding Model</h4>
        <p>
          The embedding model converts text into numbers so that similarity comparisons can be
          made. It is used when indexing reference narratives and when retrieving similar examples
          during scoring. The default model is <code>qwen3-embedding:0.6b</code> running via Ollama
          locally — no internet connection is required.
        </p>
        <div className="docs-callout docs-callout-warn">
          <strong>Warning:</strong> Changing the embedding model requires you to re-upload all
          reference files. The old embeddings are incompatible with a different model. The backend
          automatically re-initialises the vector store tables when you change the model.
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
          <div className="docs-faq-q">Layer 3 is not showing even though I uploaded financial data.</div>
          <div className="docs-faq-a">
            Layer 3 matches on the Unique ID. Make sure the ID you enter when scoring (e.g.{" "}
            <code>PROJ-001</code>) exactly matches a value in your financial data file's ID column.
            The match is case-insensitive but must otherwise be exact — no partial matches. Check
            the Standards page to confirm the financial data upload shows as active with the correct
            record count.
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
          <div className="docs-faq-q">My custom rules document was uploaded but default rubric is still being used.</div>
          <div className="docs-faq-a">
            Go to <strong>Standards</strong> and check that the Compliance Rules panel shows the
            "Active" badge and a criteria count greater than zero. If the upload succeeded but
            criteria count is 0, the AI could not find any parseable criteria in the document —
            try restructuring it as a numbered or bulleted list with a clear criterion name followed
            by a description on the same or next line.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">What file types can I upload?</div>
          <div className="docs-faq-a">
            <strong>Single scoring (Local File):</strong> <code>.txt</code>, <code>.docx</code>, <code>.pdf</code>,
            and spreadsheets (<code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>).<br />
            <strong>Batch scoring:</strong> <code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>, <code>.docx</code>, <code>.pdf</code>.<br />
            <strong>Reference Library:</strong> <code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>.<br />
            <strong>Standards — Rules:</strong> <code>.docx</code>, <code>.pdf</code>, <code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>.<br />
            <strong>Standards — Financial:</strong> <code>.xlsx</code>, <code>.xls</code>, <code>.csv</code>.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">Ollama scoring fails with a 404 error.</div>
          <div className="docs-faq-a">
            This means the model requested is not installed in your local Ollama. Run{" "}
            <code>ollama list</code> to see what is available, then select a matching model in
            the LLM dropdown. For this deployment the available chat models are{" "}
            <code>qwen3:4b</code>, <code>llama3.2:3b</code>, and <code>qwen3:8b</code>.
            Make sure <code>ollama serve</code> is running before scoring.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">Can multiple people use the same account?</div>
          <div className="docs-faq-a">
            Each person should have their own account — analytics, scoring history, standards, and
            financial data are all stored per user. Administrators can create and manage accounts
            from the Admin Panel.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">How long does scoring take?</div>
          <div className="docs-faq-a">
            A single narrative typically takes 5–20 seconds depending on the LLM provider and
            narrative length. When Layer 3 is active, add roughly 5–10 seconds for the financial
            check. Batch jobs depend on the number of rows — expect roughly 10–20 seconds per row.
            Groq is the fastest provider if speed is a priority.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">My score seems inconsistent between runs.</div>
          <div className="docs-faq-a">
            AI models have some variability in their responses. Scores can vary by ±0.5 points
            between runs of the same text. This is normal. Check the{" "}
            <strong>Analytics → AI Performance Drift</strong> tab to see if variance has increased
            recently — a sudden change in score variance can indicate a model or prompt change.
          </div>
        </div>

        <div className="docs-faq-item">
          <div className="docs-faq-q">The drift chart shows a sudden score change but the content hasn't changed.</div>
          <div className="docs-faq-a">
            This is usually caused by: (1) a provider or model switch — check the Provider Changes
            panel on the drift tab; (2) a prompt update — look for a change in the prompt hash
            column of the exported audit CSV; or (3) a change in the active rubric (switching from
            default to custom rules or vice versa). The <code>has_custom_rules</code> column in the
            audit CSV shows when this changed.
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