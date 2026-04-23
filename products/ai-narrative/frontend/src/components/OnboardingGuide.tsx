import { BarChart3, BookOpen, CheckCircle2, Layers, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { completeOnboarding } from "../services/api";
import { useAppState } from "../context/AppStateContext";

const STEPS = [
  {
    icon: <Sparkles size={28} color="var(--bsbi-red)" />,
    title: "Score a Single Narrative",
    description:
      "Go to Score Narrative in the sidebar. Enter a unique ID for your piece of work, then provide the narrative text by pasting it directly, uploading a document (Word, PDF, or plain text), or selecting a file from SharePoint. Click Run AI Score to get your results.",
    tip: "The unique ID can be any reference code you use — a project number, case ID, or any identifier that makes sense to your team.",
  },
  {
    icon: <Layers size={28} color="var(--bsbi-red)" />,
    title: "Run a Batch Score",
    description:
      "Go to Batch Score. Upload an Excel or CSV file that contains one narrative per row. The system automatically detects which column holds the ID and which holds the narrative text — you confirm or correct the mapping before running. Results for every row appear in an expandable table, and you can export them as a CSV.",
    tip: "If the column detection looks wrong, click 'AI Detection' for a smarter guess based on the actual cell values rather than just the column name.",
  },
  {
    icon: <BookOpen size={28} color="var(--bsbi-red)" />,
    title: "Build Your Reference Library",
    description:
      "Go to Reference Library. Upload an Excel or CSV file containing approved, high-quality narratives. These are your 'gold standard' examples. The system indexes them and uses them during scoring to detect abnormalities — things your narrative is missing or doing differently from the approved examples.",
    tip: "Upload reference files that are relevant to the type of narratives you score. The closer the match, the more accurate the abnormality detection.",
  },
  {
    icon: <BarChart3 size={28} color="var(--bsbi-red)" />,
    title: "Review Your Analytics",
    description:
      "Go to Analytics to see a summary of all your scoring activity: how many narratives you have scored, how they break down into pass, warning, and fail, and your average compliance score. The Recent Scores table shows your last 20 scoring runs.",
    tip: "If your pass rate is low, check the Quality Issues in individual scores — common patterns can point to systematic problems in how narratives are written.",
  },
];

type Props = {
  onDismiss: () => void; // session-only (skip)
};

export default function OnboardingGuide({ onDismiss }: Props) {
  const { token, setUser, user } = useAppState();
  const [step, setStep] = useState(0);
  const [completing, setCompleting] = useState(false);

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  const handleComplete = async () => {
    setCompleting(true);
    try {
      await completeOnboarding({ token: token! });
      // Update local user state so the guide doesn't show again
      if (user) setUser({ ...user, onboarding_completed: true });
    } catch {
      // Non-fatal — still close
    } finally {
      setCompleting(false);
      onDismiss();
    }
  };

  return (
    <div className="onboarding-backdrop">
      <div className="onboarding-modal">
        {/* Header */}
        <div className="onboarding-header">
          <div>
            <div className="onboarding-label">Getting Started — Step {step + 1} of {STEPS.length}</div>
            <h2 className="onboarding-title">Welcome to AI Narrative Search</h2>
          </div>
          <button
            type="button"
            className="onboarding-skip"
            onClick={onDismiss}
            title="Skip for now — you'll see this again next time you log in"
          >
            <X size={16} /> Skip for now
          </button>
        </div>

        {/* Step dots */}
        <div className="onboarding-dots">
          {STEPS.map((_, i) => (
            <button
              key={i}
              type="button"
              className={`onboarding-dot${i === step ? " active" : ""}${i < step ? " done" : ""}`}
              onClick={() => setStep(i)}
              aria-label={`Go to step ${i + 1}`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="onboarding-body">
          <div className="onboarding-icon">{current.icon}</div>
          <h3 className="onboarding-step-title">{current.title}</h3>
          <p className="onboarding-step-desc">{current.description}</p>
          {current.tip && (
            <div className="onboarding-tip">
              <span className="onboarding-tip-label">💡 Tip</span>
              {current.tip}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="onboarding-actions">
          {step > 0 && (
            <button type="button" className="btn btn-secondary" onClick={() => setStep((s) => s - 1)}>
              ← Back
            </button>
          )}
          <div style={{ flex: 1 }} />
          {!isLast ? (
            <button type="button" className="btn btn-primary" onClick={() => setStep((s) => s + 1)}>
              Next →
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void handleComplete()}
              disabled={completing}
            >
              <CheckCircle2 size={14} /> Got it, let's go!
            </button>
          )}
        </div>
      </div>
    </div>
  );
}