import { useEffect, useState } from 'react';
import { Check } from '@phosphor-icons/react';
import { api, formatApiError } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { PageHeader } from '@/components/ui-extras';
import { SETTINGS } from '@/constants/testIds';

export default function Settings() {
  const { user, updatePreferredModel } = useAuth();
  const [models, setModels] = useState([]);
  const [selected, setSelected] = useState(user?.preferred_model || '');
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.get('/models').then((r) => setModels(r.data.models));
  }, []);

  const save = async () => {
    setErr('');
    setSaved(false);
    try {
      await updatePreferredModel(selected);
      setSaved(true);
      setTimeout(() => setSaved(false), 2400);
    } catch (e) {
      setErr(formatApiError(e?.response?.data?.detail));
    }
  };

  return (
    <div data-testid={SETTINGS.root}>
      <PageHeader subtitle="Konfiguracja" title="Ustawienia konta" />

      <div className="px-8 py-6 max-w-2xl">
        <div className="border border-border bg-ink-800 p-6 mb-6">
          <div className="overline mb-3">Konto</div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <Row label="Imię i nazwisko" value={user?.full_name} />
            <Row label="E-mail" value={user?.email} mono />
            <Row label="ID użytkownika" value={user?.id} mono />
          </div>
        </div>

        <div className="border border-border bg-ink-800 p-6 mb-6">
          <div className="overline mb-3">Domyślny model AI</div>
          <p className="text-sm text-ink-300 mb-4">Wybrany model jest preselectowany w widoku analizy meczu. Możesz zmienić go w każdej chwili.</p>
          <div className="space-y-2 mb-4" data-testid={SETTINGS.modelSelect}>
            {models.map((m) => (
              <label key={m.key} className={`flex items-center justify-between border px-4 py-3 cursor-pointer transition-colors ${selected === m.key ? 'border-[#0066FF] bg-ink-700' : 'border-border hover:bg-ink-700'}`}>
                <div>
                  <div className="font-display font-semibold">{m.label}</div>
                  <div className="overline mt-1">{m.provider} · {m.key}</div>
                </div>
                <input type="radio" name="model" value={m.key} checked={selected === m.key} onChange={(e) => setSelected(e.target.value)} className="accent-[#0066FF]" />
              </label>
            ))}
          </div>
          {err && <div className="border border-edgeDown text-edgeDown text-xs px-3 py-2 mb-3 font-mono">{err}</div>}
          <div className="flex items-center gap-3">
            <button data-testid={SETTINGS.saveButton} onClick={save} className="bg-[#0066FF] hover:bg-[#3b82f6] px-5 py-2.5 text-xs uppercase tracking-wider font-display">
              Zapisz
            </button>
            {saved && (
              <div className="text-edgeUp text-xs flex items-center gap-1.5">
                <Check size={14} weight="bold" /> Zapisano
              </div>
            )}
          </div>
        </div>

        <div className="border border-border bg-ink-800 p-6">
          <div className="overline mb-3">Edge AI · O modelu</div>
          <p className="text-sm text-ink-300 leading-relaxed">
            Silnik łączy cztery filary: <span className="text-white">tempo gry</span> (posiadanie, strzały, PPDA), <span className="text-white">mikrotrendy kursów</span> (drift 1/X/2 i wolatylność), <span className="text-white">reakcję zespołów</span> (forma last-5 z recency weighting) oraz <span className="text-white">dane historyczne</span> (H2H). Każdy filar ma wagę w blendzie probabilistycznym; wynikowa różnica względem implied probability rynku daje wskaźnik <span className="text-edgeUp">Edge</span>. Wybrany LLM interpretuje sygnały i generuje tezę w języku polskim.
          </p>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div>
      <div className="overline mb-1">{label}</div>
      <div className={mono ? 'font-mono text-sm' : 'text-sm'}>{value}</div>
    </div>
  );
}
