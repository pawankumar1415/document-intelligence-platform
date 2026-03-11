export type ParsedSection = {
  heading: string;
  body: string;
};

export type ParsedDocument = {
  filename: string;
  file_type: "docx" | "txt";
  title: string;
  text: string;
  sections: ParsedSection[];
  word_count: number;
  paragraph_count: number;
};

export type ParseResponse = {
  document: ParsedDocument;
  project_id?: number;
  document_id?: number;
};

export type DocumentInput = {
  title: string;
  text: string;
  sections: ParsedSection[];
};

export type GenerateSowRequest = {
  client_name: string;
  project_name: string;
  source_document: DocumentInput;
  assumptions: string[];
  project_id?: number;
  llm_provider: LLMProvider;
};

export type GeneratePptxRequest = {
  deck_title: string;
  subtitle?: string;
  source_document: DocumentInput;
  max_content_slides: number;
  project_id?: number;
  llm_provider: LLMProvider;
};

export type LLMProvider = "openai" | "groq" | "azure_openai";

export type GeneratedSection = {
  title: string;
  paragraphs: string[];
  bullets: string[];
};

export type GeneratedSlide = {
  title: string;
  bullets: string[];
};

export type GenerateResult = {
  artifact_type: "sow" | "pptx";
  file_path: string;
  artifact_name: string;
  download_url: string;
  summary: string;
  artifact_id?: number;
  project_id?: number;
  sections: GeneratedSection[];
  slides: GeneratedSlide[];
};

export type OutputArtifact = GenerateResult & {
  id: string;
  created_at: string;
};

export type AuthUser = {
  id: number;
  email: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
  user: AuthUser;
};
