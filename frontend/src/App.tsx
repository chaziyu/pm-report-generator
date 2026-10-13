import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { NewPmPage } from './pages/NewPmPage';
import { UploadPage } from './pages/UploadPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { ReviewPage } from './pages/ReviewPage';
import { ResultPage } from './pages/ResultPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/session/:id/details" element={<NewPmPage />} />
        <Route path="/session/:id/upload" element={<UploadPage />} />
        <Route path="/session/:id/analyze" element={<AnalysisPage />} />
        <Route path="/session/:id/review" element={<ReviewPage />} />
        <Route path="/session/:id/result" element={<ResultPage />} />
        {/* Legacy redirect */}
        <Route path="/session/:id/new" element={<Navigate to="../details" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
