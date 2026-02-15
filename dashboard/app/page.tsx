'use client';

import { useState } from 'react';
import PreferencesModal from '@/components/PreferencesModal';
import CookingInput from '@/components/CookingInput';
import RecommendationsGrid, { Recommendation } from '@/components/RecommendationsGrid';

export default function Dashboard() {
  const [isPreferencesModalOpen, setIsPreferencesModalOpen] = useState(false);
  const [userPreferences, setUserPreferences] = useState<string[]>([
    'Nut Free',
    'Keto',
    'No Spicy'
  ]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [aiMessage, setAiMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [playingCardId, setPlayingCardId] = useState<number | null>(null);

  const handleSavePreferences = (preferences: string[]) => {
    setUserPreferences(preferences);
    console.log('Saved preferences:', preferences);
  };

  const handleSubmit = async (userInput: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userInput,
          preferences: userPreferences,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }

      const data = await response.json();

      if (data.recommendations && data.recommendations.length > 0) {
        setRecommendations(
          data.recommendations.map((rec: any, index: number) => ({
            id: index + 1,
            name: rec.name,
            imageUrl: rec.imageUrl || '/images/dishes/placeholder.png',
            description: rec.description,
            recipeTaskQueue: Array.isArray(rec.recipeTaskQueue) ? rec.recipeTaskQueue : []
          }))
        );
      }

      if (data.message) {
        setAiMessage(data.message);
      }
    } catch (error) {
      console.error('Error getting recommendations:', error);
      setError(error instanceof Error ? error.message : 'Failed to get recommendations. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCook = (item: Recommendation) => {
    console.log(`Sending recipeTaskQueue to 100.71.232.77:9005 →`, item.recipeTaskQueue);
    fetch('/api/send-task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        recipeTaskQueue: item.recipeTaskQueue,
        host: '100.71.232.77',
        port: 9005,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.error) console.error('Send failed:', data.error);
        else console.log('Task queue sent for:', item.name);
      })
      .catch((err) => console.error('Send error:', err));
  };

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{
        backgroundColor: isDarkMode ? '#151514ff' : 'rgb(249, 250, 251)',
      }}
    >
      <main className={`max-w-4xl mx-auto px-6 flex flex-col ${
        recommendations.length === 0 && !isLoading
          ? 'py-12 justify-center min-h-screen'
          : 'py-8'
      }`}>
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <img
            src={isDarkMode ? '/images/remy_logo_dark.svg' : '/images/remy_logo.svg'}
            alt="Logo"
            className="object-contain cursor-pointer transition-all"
            style={{
              height: '100px',
              filter: 'drop-shadow(0 0 0px rgba(175, 67, 29, 0))',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.filter = 'drop-shadow(0 0 20px rgba(175, 67, 29, 0.8))';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.filter = 'drop-shadow(0 0 0px rgba(175, 67, 29, 0))';
            }}
            onClick={() => setIsDarkMode(!isDarkMode)}
          />
        </div>

        {/* Greeting */}
        <p className={`mb-2 text-lg transition-colors ${
          isDarkMode ? 'text-gray-400' : 'text-gray-600'
        }`}>hello Allen</p>
        <h1 className={`text-4xl font-semibold mb-8 transition-colors ${
          isDarkMode ? 'text-white' : 'text-gray-900'
        }`}>
          What do you wish to cook?
        </h1>

        <CookingInput
          isDarkMode={isDarkMode}
          userPreferences={userPreferences}
          isLoading={isLoading}
          onSubmit={handleSubmit}
          onOpenPreferences={() => setIsPreferencesModalOpen(true)}
        />

        <RecommendationsGrid
          recommendations={recommendations}
          isLoading={isLoading}
          isDarkMode={isDarkMode}
          playingCardId={playingCardId}
          onTogglePlay={(id) => setPlayingCardId(playingCardId === id ? null : id)}
          onCook={handleCook}
        />
      </main>

      <PreferencesModal
        isOpen={isPreferencesModalOpen}
        onClose={() => setIsPreferencesModalOpen(false)}
        onSave={handleSavePreferences}
        initialPreferences={userPreferences}
        isDarkMode={isDarkMode}
      />
    </div>
  );
}
