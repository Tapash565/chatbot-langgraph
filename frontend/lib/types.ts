/** Type definitions for the chatbot. */

export interface Message {
  id: string;
  type: 'user' | 'ai' | 'tool' | 'tool_call';
  content: string;
  toolName?: string;
  toolResult?: string;
}

export interface Thread {
  id: string;
  name: string;
  lastActive?: string;
}

export interface DocumentMetadata {
  has_document: boolean;
  filename?: string;
  documents?: number;
  chunks?: number;
}

export interface PDFUploadResponse {
  success: boolean;
  filename: string;
  documents: number;
  chunks: number;
  message: string;
}

export interface StreamEvent {
  type: 'ai' | 'tool_call' | 'tool' | 'done' | 'error';
  content?: string;
  tool_name?: string;
  tool_result?: string;
  tool_args?: Record<string, unknown>;
  error?: string;
}
