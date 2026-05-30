import { NavLink, useNavigate } from 'react-router-dom';
import {
  GridFour,
  Plus,
  Receipt,
  ChartLineUp,
  Gear,
  SignOut,
  Lightning,
} from '@phosphor-icons/react';
import { useAuth } from '@/contexts/AuthContext';
import { NAV, LOGOUT } from '@/constants/testIds';

const ITEMS = [
  { to: '/', label: 'Dashboard', icon: GridFour, testid: NAV.linkDashboard, end: true },
  { to: '/add', label: 'Nowy mecz', icon: Plus, testid: NAV.linkAddMatch },
  { to: '/bets', label: 'Zakłady', icon: Receipt, testid: NAV.linkBets },
  { to: '/stats', label: 'Statystyki', icon: ChartLineUp, testid: NAV.linkStats },
  { to: '/settings', label: 'Ustawienia', icon: Gear, testid: NAV.linkSettings },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <aside className="w-60 shrink-0 border-r border-border bg-ink-900 flex flex-col">
      <div
        data-testid={NAV.sidebarLogo}
        className="px-5 py-5 border-b border-border flex items-center gap-2 cursor-pointer"
        onClick={() => nav('/')}
      >
        <Lightning size={20} weight="fill" className="text-[#0066FF]" />
        <div>
          <div className="font-display font-black text-base tracking-tight leading-none">EDGE / AI</div>
          <div className="overline mt-1">Football edge detector</div>
        </div>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {ITEMS.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            end={it.end}
            data-testid={it.testid}
            className={({ isActive }) =>
              `group flex items-center gap-3 px-3 py-2 text-sm transition-colors duration-100 ${
                isActive
                  ? 'bg-ink-700 text-white border-l-2 border-[#0066FF] pl-[10px]'
                  : 'text-ink-300 hover:bg-ink-800 hover:text-white border-l-2 border-transparent'
              }`
            }
          >
            <it.icon size={16} weight="bold" />
            <span>{it.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border p-3">
        <div data-testid={NAV.userMenu} className="mb-2 px-2">
          <div className="text-sm truncate font-medium">{user?.full_name}</div>
          <div className="overline truncate">{user?.email}</div>
        </div>
        <button
          data-testid={LOGOUT.button}
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs uppercase tracking-wider text-ink-300 hover:text-edgeDown hover:bg-ink-800 transition-colors"
        >
          <SignOut size={14} weight="bold" />
          Wyloguj
        </button>
      </div>
    </aside>
  );
}
