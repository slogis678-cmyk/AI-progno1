import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Lightning, ArrowRight } from '@phosphor-icons/react';
import { useAuth } from '@/contexts/AuthContext';
import { REGISTER } from '@/constants/testIds';
import { formatApiError } from '@/lib/api';

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    if (password !== confirm) {
      setErr('Hasła nie są identyczne');
      return;
    }
    setLoading(true);
    try {
      await register(email, password, name);
      nav('/', { replace: true });
    } catch (e2) {
      setErr(formatApiError(e2?.response?.data?.detail) || 'Rejestracja nie powiodła się');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-ink-900 text-white p-8">
      <form onSubmit={submit} className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-10">
          <Lightning size={22} weight="fill" className="text-[#0066FF]" />
          <span className="font-display font-black tracking-tighter text-xl">EDGE / AI</span>
        </div>
        <div className="overline mb-2">Rejestracja</div>
        <h2 className="font-display text-3xl font-black tracking-tighter mb-8">Utwórz konto analityka.</h2>

        <Field label="Imię i nazwisko">
          <input
            data-testid={REGISTER.nameInput}
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-ink-800 border border-border px-3 py-2.5 text-sm focus:outline-none focus:border-[#0066FF]"
          />
        </Field>
        <Field label="E-mail">
          <input
            data-testid={REGISTER.emailInput}
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-ink-800 border border-border px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-[#0066FF]"
          />
        </Field>
        <Field label="Hasło">
          <input
            data-testid={REGISTER.passwordInput}
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-ink-800 border border-border px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-[#0066FF]"
          />
        </Field>
        <Field label="Powtórz hasło">
          <input
            data-testid={REGISTER.passwordConfirmInput}
            type="password"
            required
            minLength={6}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="w-full bg-ink-800 border border-border px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-[#0066FF]"
          />
        </Field>

        {err && (
          <div className="border border-edgeDown text-edgeDown text-xs px-3 py-2 mb-4 font-mono">{err}</div>
        )}

        <button
          data-testid={REGISTER.submitButton}
          disabled={loading}
          className="w-full bg-[#0066FF] hover:bg-[#3b82f6] disabled:opacity-60 text-white font-display font-semibold tracking-wide py-3 transition-colors flex items-center justify-center gap-2"
        >
          {loading ? 'Tworzenie konta…' : (<>Utwórz konto <ArrowRight size={16} weight="bold" /></>)}
        </button>

        <div className="mt-6 text-xs text-ink-300 flex items-center justify-between">
          <span>Masz już konto?</span>
          <Link data-testid={REGISTER.loginLink} to="/login" className="text-white hover:text-[#0066FF]">
            Zaloguj się →
          </Link>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block mb-4">
      <div className="overline mb-2">{label}</div>
      {children}
    </label>
  );
}
