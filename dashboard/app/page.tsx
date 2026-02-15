'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import RecommendationCards from '@/components/RecommendationCards';
import PreferencesPanel from '@/components/PreferencesPanel';
import StatsSection from '@/components/StatsSection';
import PreviousDishes from '@/components/PreviousDishes';
import PreferencesModal from '@/components/PreferencesModal';

export default function Dashboard() {
  const [isPreferencesModalOpen, setIsPreferencesModalOpen] = useState(false);
  const [userPreferences, setUserPreferences] = useState<string[]>([
    'Low Sugar',
    'Low Sodium',
    'Medium Rare'
  ]);

  const handleSavePreferences = (preferences: string[]) => {
    setUserPreferences(preferences);
    // TODO: Send preferences to AI backend
    console.log('Saved preferences:', preferences);
  };

  return (
    <div className="flex min-h-screen">
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
          <PreferencesPanel
            preferences={userPreferences}
            onEdit={() => setIsPreferencesModalOpen(true)}
          />

          {/* Statistics */}
          <StatsSection />
        </div>
      </main>

      {/* Right Sidebar - Previous Dishes */}
      <PreviousDishes />

      {/* Preferences Modal */}
      <PreferencesModal
        isOpen={isPreferencesModalOpen}
        onClose={() => setIsPreferencesModalOpen(false)}
        onSave={handleSavePreferences}
        initialPreferences={userPreferences}
      />
    </div>
  );
}
