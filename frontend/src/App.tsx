import { useState } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import LiveDashboard from './views/LiveDashboard';
import EscalationsView from './views/EscalationsView';
import HistoryView from './views/HistoryView';
import SettingsView from './views/SettingsView';
import ChaosView from './views/ChaosView';
import './index.css';

export default function App() {
  const [currentView, setCurrentView] = useState('live');

  return (
    <>
      <Sidebar currentView={currentView} onViewChange={setCurrentView} />
      <main className="main-content">
        <TopBar currentView={currentView} />
        {currentView === 'live' && <LiveDashboard onViewChange={setCurrentView} />}
        {currentView === 'escalations' && <EscalationsView />}
        {currentView === 'history' && <HistoryView />}
        {currentView === 'settings' && <SettingsView />}
        {currentView === 'chaos' && <ChaosView />}
      </main>
    </>
  );
}
