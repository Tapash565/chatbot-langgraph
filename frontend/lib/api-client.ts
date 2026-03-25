/** API client for communicating with the FastAPI backend. */
import { Thread, DocumentMetadata, PDFUploadResponse, StreamEvent, ThreadMessagesResponse } from './types';

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const API_BASE = RAW_API_BASE.endsWith('/api') ? RAW_API_BASE : `${RAW_API_BASE}/api`;

function normalizeThread(raw: Record<string, unknown>): Thread {
  return {
    id: String(raw.id ?? raw.thread_id ?? ''),
    name: String(raw.name ?? 'Untitled Chat'),
    lastActive: typeof raw.lastActive === 'string'
      ? raw.lastActive
      : typeof raw.last_active === 'string'
        ? raw.last_active
        : undefined,
  };
}

/**
 * Stream chat messages using Server-Sent Events.
 */
export async function* streamChat(
  message: string,
  threadId: string
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
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
  const response = await fetch(`${API_BASE}/threads`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to fetch threads: ${response.status} ${text}`);
  }
  const data = await response.json();
  return Array.isArray(data.threads)
    ? data.threads
        .map((thread: Record<string, unknown>) => normalizeThread(thread))
        .filter((thread: Thread) => thread.id.length > 0)
    : [];
}

/**
 * Create a new thread.
 */
export async function createThread(name?: string): Promise<Thread> {
  const response = await fetch(`${API_BASE}/threads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`Failed to create thread: ${response.status} ${err.detail || response.statusText}`);
  }
  return normalizeThread(await response.json() as Record<string, unknown>);
}

/**
 * Delete a thread.
 */
export async function deleteThread(threadId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/threads/${threadId}`, {
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
  const response = await fetch(`${API_BASE}/threads/${threadId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`Failed to rename thread: ${response.status} ${err.detail || response.statusText}`);
  }
  return normalizeThread(await response.json() as Record<string, unknown>);
}

/**
 * Upload a PDF file for a thread.
 */
export async function uploadPDF(threadId: string, file: File): Promise<PDFUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('thread_id', threadId);

  const response = await fetch(`${API_BASE}/pdf/upload`, {
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
  const response = await fetch(`${API_BASE}/threads/${threadId}/document`);
  if (!response.ok) {
    throw new Error(`Failed to fetch document metadata: ${response.status}`);
  }
  return response.json();
}

/**
 * Get message history for a thread.
 */
export async function getThreadMessages(threadId: string): Promise<ThreadMessagesResponse> {
  const response = await fetch(`${API_BASE}/threads/${threadId}/messages`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to fetch thread messages: ${response.status} ${text}`);
  }
  return response.json();
}

/**
 * Check API health.
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
