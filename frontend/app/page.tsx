/** Main page with sidebar and chat area. */
import Sidebar from '@/components/Sidebar';
import ChatArea from '@/components/ChatArea';
import PdfUploader from '@/components/PdfUploader';

export default function Home() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <ChatArea />
      </div>
    </div>
  );
}
