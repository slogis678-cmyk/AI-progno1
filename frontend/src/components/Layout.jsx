import Sidebar from './Sidebar';

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex bg-ink-900 text-white">
      <Sidebar />
      <main className="flex-1 min-w-0 overflow-x-hidden">
        {children}
      </main>
    </div>
  );
}
