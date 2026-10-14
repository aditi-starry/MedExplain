import { useEffect, useState } from 'react';
import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { useHashRoute } from './hooks/useHashRoute';
import { useI18n } from './i18n';
import { HomePage } from './pages/HomePage';
import { ReportPage } from './pages/ReportPage';
import { UploadPage } from './pages/UploadPage';
import { getHealth } from './services/api';
import { errorMessage, loadSampleFile, uploadAndExtract } from './services/reportFlow';
import { listSessionReports } from './services/session';
import { Alert } from './components/ui';

export function App() {
  const { t } = useI18n();
  const [route, navigate] = useHashRoute();
  const [retentionHours, setRetentionHours] = useState(24);
  const [ocrAvailable, setOcrAvailable] = useState<boolean | null>(null);
  const [sampleBusy, setSampleBusy] = useState(false);
  const [sampleError, setSampleError] = useState<string | null>(null);
  const lastReport = route.name === 'report' ? route.reportId : listSessionReports().slice(-1)[0]?.reportId ?? null;

  // Also wakes a sleeping free-tier backend early
  useEffect(() => {
    getHealth()
      .then((h) => {
        setRetentionHours(h.retentionHours);
        setOcrAvailable(h.ocrAvailable);
      })
      .catch(() => setOcrAvailable(null));
  }, []);

  const trySample = async () => {
    setSampleBusy(true);
    setSampleError(null);
    try {
      const file = await loadSampleFile('/sample_lab_report.pdf', 'Fictional_Sample_Lab_Report.pdf');
      const { auth } = await uploadAndExtract(file);
      navigate({ name: 'report', reportId: auth.reportId });
    } catch (err) {
      setSampleError(errorMessage(err, t));
    } finally {
      setSampleBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header route={route} onNavigate={navigate} currentReportId={lastReport} />
      <main id="main" className="flex-1" tabIndex={-1}>
        {(sampleBusy || sampleError) && route.name === 'home' && (
          <div className="mx-auto max-w-6xl px-4 pt-6 sm:px-6">
            {sampleBusy ? <Alert tone="info">{t('steps.extract')}</Alert> : <Alert tone="danger">{sampleError}</Alert>}
          </div>
        )}
        {route.name === 'home' && <HomePage onUpload={() => navigate({ name: 'upload' })} onSample={trySample} retentionHours={retentionHours} />}
        {route.name === 'upload' && (
          <UploadPage onDone={(id) => navigate({ name: 'report', reportId: id })} retentionHours={retentionHours} ocrAvailable={ocrAvailable} />
        )}
        {route.name === 'report' && (
          <ReportPage key={route.reportId} reportId={route.reportId} retentionHours={retentionHours} onUploadNew={() => navigate({ name: 'upload' })} />
        )}
      </main>
      <Footer />
    </div>
  );
}

export default App;