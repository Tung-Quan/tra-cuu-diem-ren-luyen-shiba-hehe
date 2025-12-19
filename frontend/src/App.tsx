import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import SearchPage from "./pages/SearchPage";
import MySQLSearchPage from "./pages/MySQLSearchPage";
import AddLinkPage from "./pages/AddLinkPage";
import SheetsPage from "./pages/SheetsPage";
import HealthPage from "./pages/HealthPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/mysql" element={<MySQLSearchPage />} />
        <Route path="/add-link" element={<AddLinkPage />} />
        <Route path="/sheets" element={<SheetsPage />} />
        <Route path="/health" element={<HealthPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
