'use client';

import { useSyncExternalStore } from 'react';
import Sidebar from '@/components/Sidebar';
import ChatArea from '@/components/ChatArea';

function LoadingShell() {
  return (
    <div className="flex h-screen">
      <div className="w-64 h-screen bg-sidebar-bg border-r border-border flex flex-col text-foreground" />
      <div className="flex-1 flex flex-col h-screen bg-background">
        <header className="sticky top-0 z-10 flex items-center justify-between p-3 border-b border-border bg-background/80 backdrop-blur-md px-6">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">LangGraph AI</span>
          </div>
        </header>
        <div className="flex-1" />
        <div className="w-full max-w-3xl mx-auto p-4 pb-8">
          <div className="relative flex flex-col w-full bg-sidebar-bg border border-border rounded-2xl p-1 shadow-sm">
            <textarea
              value=""
              readOnly
              disabled
              placeholder="Message LangGraph AI..."
              className="w-full px-4 py-3 bg-transparent border-none outline-none text-[15px] resize-none chat-input-textarea placeholder-gray-500"
              rows={1}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function HomeClient() {
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  if (!mounted) {
    return <LoadingShell />;
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <ChatArea />
      </div>
    </div>
  );
}
