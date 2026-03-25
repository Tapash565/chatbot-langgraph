/** Message component for displaying individual messages. */
import type { Message } from '@/lib/types';

interface MessageProps {
  message: Message;
}

export default function Message({ message }: MessageProps) {
  const isUser = message.type === 'user';
  const isTool = message.type === 'tool';
  const isToolCall = message.type === 'tool_call';

  if (isToolCall) {
    return (
      <div className="flex items-start gap-4 mb-6 px-4 md:px-6 lg:px-8 max-w-3xl mx-auto w-full">
        <div className="w-8 h-8 rounded-full bg-amber-600/20 shrink-0 flex items-center justify-center border border-amber-600/30">
          <svg className="w-4 h-4 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.423 20.25l7.197-2.135a.563.563 0 00.312-.922L12.641 9.513a.562.562 0 010-.782l6.29-6.953a.562.562 0 00-.311-.922l-7.197 2.135a.563.563 0 00-.312.922l6.29 6.953a.562.562 0 010 .782l-6.29 6.953a.562.562 0 00.311.922z" />
          </svg>
        </div>
        <div className="flex-1 text-sm text-amber-200/70 italic pt-1">
          Calling tool: <span className="font-semibold text-amber-200">{message.toolName}</span>
        </div>
      </div>
    );
  }

  if (isTool) {
    return (
      <div className="flex items-start gap-4 mb-6 px-4 md:px-6 lg:px-8 max-w-3xl mx-auto w-full">
        <div className="w-8 h-8 rounded-full bg-purple-600/20 shrink-0 flex items-center justify-center border border-purple-600/30">
          <svg className="w-4 h-4 text-purple-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
          </svg>
        </div>
        <div className="flex-1 bg-purple-900/10 border border-purple-700/30 rounded-xl p-4 text-sm text-purple-200 overflow-hidden">
          <div className="font-semibold mb-2 text-purple-400">Tool Result: {message.toolName}</div>
          <div className="whitespace-pre-wrap font-mono text-xs opacity-90">{message.content}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`group w-full py-6 transition-colors ${isUser ? '' : 'bg-transparent'}`}>
      <div className="flex items-start gap-4 px-4 md:px-6 lg:px-8 max-w-3xl mx-auto w-full">
        <div className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center font-bold text-xs text-white ${isUser ? 'bg-blue-600' : 'bg-accent text-white'
          }`}>
          {isUser ? 'U' : (
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5.5-2.5l7.5-7.5-7.5-7.5 1.5-1.5 9 9-9 9-1.5-1.5z" />
            </svg>
          )}
        </div>
        <div className="flex-1 pt-1 overflow-hidden">
          <div className="font-semibold text-sm mb-1 text-gray-400">
            {isUser ? 'You' : 'Assistant'}
          </div>
          <div className="prose prose-invert max-w-none text-[15px] leading-relaxed whitespace-pre-wrap wrap-break-word">
            {message.content}
          </div>
        </div>
      </div>
    </div>
  );
}
