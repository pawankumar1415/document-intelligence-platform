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
};

export type GeneratePptxRequest = {
  deck_title: string;
  subtitle?: string;
  source_document: DocumentInput;
  max_content_slides: number;
};

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
  sections: GeneratedSection[];
  slides: GeneratedSlide[];
};

export type OutputArtifact = GenerateResult & {
  id: string;
  created_at: string;
};
