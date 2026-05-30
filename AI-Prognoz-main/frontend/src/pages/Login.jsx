import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Lightning, ArrowRight } from '@phosphor-icons/react';
import { useAuth } from '@/contexts/AuthContext';
import { LOGIN } from '@/constants/testIds';
import { formatApiError } from '@/lib/api';

const BG_IMG = 'https://static.prod-images.emergentagent.com/jobs/74ba0711-0455-4637-84d8-808b33b04f52/images/5692fbd735d39cc7c1935adb9baa63099038a208dbfa90c05dc789b15f373fa5.png';

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState('admin@edgeai.pl');
  const [password, setPassword] = useState('admin123');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    setLoading(true);
    try {
      await login(email, password);
      const to = loc.state?.from?.pathname || '/';
      nav(to, { replace: true });
    } catch (e2) {
      setErr(formatApiError(e2?.response?.data?.detail) || 'Logowanie nie powiodło się');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-5 bg-ink-900 text-white">
      {/* Left – background visual */}
      <div className="hidden lg:flex lg:col-span-3 relative overflow-hidden border-r border-border">
        <img src={BG_IMG} alt="" className="absolute inset-0 w-full h-full object-cover opacity-60" />
        <div className="absolute inset-0 bg-gradient-to-r from-ink-900/80 via-ink-900/40 to-ink-900/80" />
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div className="flex items-center gap-2">
            <Lightning size={22} weight="fill" className="text-[#0066FF]" />
            <span className="font-display font-black tracking-tighter text-xl">EDGE / AI</span>
          </div>
          <div>
            <div className="overline mb-4">Statistical edge detection · v1.0</div>
            <h1 className="font-display text-5xl xl:text-6xl font-black tracking-tighter leading-[0.95] max-w-xl">
              Wykryj <span className="text-edgeUp">przewagę</span> tam, gdzie inni widzą tylko kurs.
            </h1>
            <p className="mt-6 text-ink-300 max-w-md text-sm leading-relaxed">
              Model AI łączy <span className="text-white">tempo gry</span>, <span className="text-white">mikrotrendy kursów</span>, <span className="text-white">reakcję zespołów</span> i <span className="text-white">dane historyczne</span> w jeden wskaźnik value-bet.
            </p>
            <div className="mt-8 grid grid-cols-3 gap-px bg-border max-w-md">
              <Metric label="Pillars" value="4" />
              <Metric label="Modele" value="3" />
              <Metric label="Sygnał" value="real-time" />
            </div>
          </div>
          <div className="overline">© Edge AI · Kontrolny pulpit analityka</div>
        </div>
      </div>

      {/* Right – form */}
      <div className="lg:col-span-2 flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm">
          <div className="overline mb-2">Logowanie</div>
          <h2 className="font-display text-3xl font-black tracking-tighter mb-8">Wejdź do terminala.</h2>

          <Field label="E-mail" testid={LOGIN.emailInput}>
            <input
              data-testid={LOGIN.emailInput}
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-ink-800 border border-border px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-[#0066FF]"
            />
          </Field>

          <Field label="Hasło" testid={LOGIN.passwordInput}>
            <input
              data-testid={LOGIN.passwordInput}
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-ink-800 border border-border px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-[#0066FF]"
            />
          </Field>

          {err && (
            <div className="border border-edgeDown text-edgeDown text-xs px-3 py-2 mb-4 font-mono">
              {err}
            </div>
          )}

          <button
            data-testid={LOGIN.submitButton}
            disabled={loading}
            className="w-full bg-[#0066FF] hover:bg-[#3b82f6] disabled:opacity-60 text-white font-display font-semibold tracking-wide py-3 transition-colors flex items-center justify-center gap-2"
          >
            {loading ? 'Łączenie…' : (<>Zaloguj <ArrowRight size={16} weight="bold" /></>)}
          </button>

          <div className="mt-6 text-xs text-ink-300 flex items-center justify-between">
            <span>Nie masz konta?</span>
            <Link data-testid={LOGIN.registerLink} to="/register" className="text-white hover:text-[#0066FF]">
              Utwórz konto →
            </Link>
          </div>

          <div className="mt-10 border-t border-border pt-4">
            <div className="overline mb-2">Demo</div>
            <div className="font-mono text-[11px] text-ink-300 leading-relaxed">
              admin@edgeai.pl<br />admin123
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, testid, children }) {
  return (
    <label className="block mb-4">
      <div className="overline mb-2">{label}</div>
      {children}
    </label>
  );
}

function Metric({ label, value }) {
  return (
    <div className="bg-ink-900 p-3">
      <div className="overline">{label}</div>
      <div className="font-mono text-base text-white mt-1">{value}</div>
    </div>
  );
}
