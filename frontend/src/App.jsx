import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

function Placeholder({ title }) {
  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50">
      <h1 className="text-2xl font-semibold text-slate-800">{title}</h1>
    </main>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Placeholder title="Library Management System" />} />
        <Route path="/login" element={<Placeholder title="Login" />} />
        <Route path="/register" element={<Placeholder title="Register" />} />
        <Route path="/books" element={<Placeholder title="Book Catalog" />} />
        <Route path="/borrowings" element={<Placeholder title="Borrowing History" />} />
        <Route path="/admin" element={<Placeholder title="Admin Dashboard" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;