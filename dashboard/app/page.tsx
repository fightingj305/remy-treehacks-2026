'use client';

import Sidebar from '@/components/Sidebar';
import RecommendationCards from '@/components/RecommendationCards';
import PreferencesPanel from '@/components/PreferencesPanel';
import StatsSection from '@/components/StatsSection';
import PreviousDishes from '@/components/PreviousDishes';

export default function Dashboard() {
  return (
    <div className="flex min-h-screen bg-white">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 p-12">
        {/* Greeting */}
        <div className="mb-12">
          <p className="text-gray-600 mb-2">Good morning, Allen</p>
          <h1 className="text-4xl font-semibold mb-8">What do you wish to cook today?</h1>

          {/* Recommendations */}
          <RecommendationCards />

          {/* Preferences */}
          <PreferencesPanel />

          {/* Statistics */}
          <StatsSection />
        </div>
      </main>

      {/* Right Sidebar - Previous Dishes */}
      <PreviousDishes />
    </div>
  );
}
