/** PDF upload component. */
'use client';

import { useState, useRef } from 'react';
import { useChatStore } from '@/lib/store';
import { uploadPDF, getThreadDocument } from '@/lib/api-client';

export default function PdfUploader() {
  const { currentThreadId, setDocument } = useChatStore();
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !currentThreadId) return;

    setUploading(true);
    setMessage('');

    try {
      const result = await uploadPDF(currentThreadId, file);
      setMessage(`Indexed: ${result.filename} (${result.chunks} chunks)`);

      // Refresh document metadata
      const doc = await getThreadDocument(currentThreadId);
      setDocument(doc);
    } catch (err) {
      setMessage(`Error: ${err instanceof Error ? err.message : 'Upload failed'}`);
    }

    setUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  if (!currentThreadId) {
    return (
      <div className="p-4 bg-gray-800 rounded-lg">
        <p className="text-gray-400 text-sm">Select a chat to upload PDFs</p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-800 rounded-lg">
      <h3 className="text-sm font-medium text-gray-200 mb-2">Upload PDF</h3>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        disabled={uploading}
        className="block w-full text-sm text-gray-400
          file:mr-4 file:py-2 file:px-4
          file:rounded-lg file:border-0
          file:text-sm file:font-medium
          file:bg-blue-600 file:text-white
          file:cursor-pointer file:transition-colors
          hover:file:bg-blue-700
          disabled:file:opacity-50"
      />
      {message && (
        <p className={`mt-2 text-sm ${message.startsWith('Error') ? 'text-red-400' : 'text-green-400'}`}>
          {message}
        </p>
      )}
    </div>
  );
}
