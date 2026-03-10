/** API client for communicating with the FastAPI backend. */
import { Thread, DocumentMetadata, PDFUploadResponse, StreamEvent } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Stream chat messages using Server-Sent Events.
 */
export async function* streamChat(
  message: string,
  threadId: string
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to stream chat');
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is null');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        try {
          yield JSON.parse(data) as StreamEvent;
        } catch {
          // Skip invalid JSON
        }
      }
    }
  }
}

/**
 * Get all threads.
 */
export async function getThreads(): Promise<Thread[]> {
  const response = await fetch(`${API_BASE}/api/threads`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to fetch threads: ${response.status} ${text}`);
  }
  const data = await response.json();
  return data.threads;
}

/**
 * Create a new thread.
 */
export async function createThread(name?: string): Promise<Thread> {
  const response = await fetch(`${API_BASE}/api/threads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`Failed to create thread: ${response.status} ${err.detail || response.statusText}`);
  }
  return response.json();
}

/**
 * Delete a thread.
 */
export async function deleteThread(threadId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/threads/${threadId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`Failed to delete thread: ${response.status} ${err.detail || response.statusText}`);
  }
}

/**
 * Rename a thread.
 */
export async function renameThread(threadId: string, name: string): Promise<Thread> {
  const response = await fetch(`${API_BASE}/api/threads/${threadId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`Failed to rename thread: ${response.status} ${err.detail || response.statusText}`);
  }
  return response.json();
}

/**
 * Upload a PDF file for a thread.
 */
export async function uploadPDF(threadId: string, file: File): Promise<PDFUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/pdf/upload?thread_id=${threadId}`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(`Failed to upload PDF: ${response.status} ${error.detail || response.statusText}`);
  }
  return response.json();
}

/**
 * Get document metadata for a thread.
 */
export async function getThreadDocument(threadId: string): Promise<DocumentMetadata> {
  const response = await fetch(`${API_BASE}/api/threads/${threadId}/document`);
  if (!response.ok) {
    throw new Error(`Failed to fetch document metadata: ${response.status}`);
  }
  return response.json();
}

/**
 * Check API health.
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE.replace('/api', '')}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
