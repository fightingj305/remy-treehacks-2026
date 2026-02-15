'use client';

import { useState, useEffect } from 'react';
import PreferencesModal from '@/components/PreferencesModal';
import RecommendationCard, { RecommendationCardSkeleton } from '@/components/RecommendationCard';

interface Recommendation {
  id: number;
  name: string;
  imageUrl: string;
}

export default function Dashboard() {
  const [isPreferencesModalOpen, setIsPreferencesModalOpen] = useState(false);
  const [userPreferences, setUserPreferences] = useState<string[]>([
    'Nut Free',
    'Keto',
    'No Spicy'
  ]);
  const [userInput, setUserInput] = useState('');
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [aiMessage, setAiMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);

  // Typing animation states
  const [placeholderText, setPlaceholderText] = useState('');
  const [currentPromptIndex, setCurrentPromptIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(true);
  const [charIndex, setCharIndex] = useState(0);

  const prompts = [
    "I want to cook a high-protein meal with chicken and vegetables",
    "I want to cook something vegan using whatever's in season right now",
    "I want to cook a keto-friendly dinner that's under 30 minutes",
    "I want to cook a traditional Korean dish but make it halal",
    "I want to cook a low-sodium Mediterranean seafood pasta for two"
  ];

  // Typing animation effect
  useEffect(() => {
    if (userInput !== '') {
      setPlaceholderText('');
      return; // Don't animate if user has typed something
    }

    const currentPrompt = prompts[currentPromptIndex];

    if (isTyping) {
      // Typing phase
      if (charIndex <= currentPrompt.length) {
        const timeout = setTimeout(() => {
          setPlaceholderText(currentPrompt.substring(0, charIndex));
          setCharIndex(charIndex + 1);
        }, 50); // Type each character every 50ms

        return () => clearTimeout(timeout);
      } else {
        // Finished typing, pause before erasing
        const pauseTimeout = setTimeout(() => {
          setIsTyping(false);
        }, 2000); // Pause for 2 seconds

        return () => clearTimeout(pauseTimeout);
      }
    } else {
      // Erasing phase
      if (charIndex > 0) {
        const timeout = setTimeout(() => {
          setPlaceholderText(currentPrompt.substring(0, charIndex - 1));
          setCharIndex(charIndex - 1);
        }, 30); // Erase faster than typing

        return () => clearTimeout(timeout);
      } else {
        // Finished erasing, move to next prompt
        setCurrentPromptIndex((prev) => (prev + 1) % prompts.length);
        setIsTyping(true);
        setCharIndex(0);
      }
    }
  }, [currentPromptIndex, isTyping, userInput, prompts, charIndex]);

  const handleSavePreferences = (preferences: string[]) => {
    setUserPreferences(preferences);
    console.log('Saved preferences:', preferences);
  };

  const handleSubmit = async () => {
    if (!userInput.trim() || isLoading) return;

    setIsLoading(true);
    setError(null); // Clear any previous errors
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
          }))
        );
      }

      if (data.message) {
        setAiMessage(data.message);
      }

      // Clear the input after successful submission
      setUserInput('');
    } catch (error) {
      console.error('Error getting recommendations:', error);
      setError(error instanceof Error ? error.message : 'Failed to get recommendations. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{
        backgroundColor: isDarkMode ? '#23231F' : 'rgb(249, 250, 251)',
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

        {/* Input Box */}
        <div
          className={`rounded-2xl p-6 shadow-sm border mb-8 transition-colors ${
            isDarkMode ? 'border-gray-700' : 'border-gray-200'
          }`}
          style={{
            backgroundColor: isDarkMode ? '#2f2f2a' : 'white',
          }}
        >
          <div className="flex items-center gap-4 mb-6">
            {/* Text Input */}
            <div className="flex-1 relative">
              {userInput === '' && (
                <div className="absolute top-0 left-0 flex items-start pt-1 pointer-events-none">
                  <span className={`text-lg transition-colors ${
                    isDarkMode ? 'text-gray-500' : 'text-gray-400'
                  }`}>
                    {placeholderText}<span className="animate-blink">|</span>
                  </span>
                </div>
              )}
              <textarea
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                className={`w-full text-lg outline-none bg-transparent resize-none overflow-y-auto transition-colors ${
                  isDarkMode ? 'text-white' : 'text-black'
                }`}
                style={{
                  height: 'calc(1.5rem * 1.5 * 2)', // Fixed 2 lines (font-size * line-height * lines)
                  lineHeight: '1.5',
                }}
                rows={2}
              />
            </div>

            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              disabled={isLoading || !userInput.trim()}
              className="text-white p-3 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: '#AF431D' }}
              onMouseEnter={(e) => !isLoading && (e.currentTarget.style.backgroundColor = '#8A3517')}
              onMouseLeave={(e) => !isLoading && (e.currentTarget.style.backgroundColor = '#AF431D')}
            >
              {isLoading ? (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="animate-spin"
                >
                  <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                  <path d="M12 2a10 10 0 0 1 10 10" strokeOpacity="0.75" />
                </svg>
              ) : (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              )}
            </button>
          </div>

          {/* Preferences */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <h2 className={`text-sm uppercase font-medium transition-colors ${
                isDarkMode ? 'text-gray-400' : 'text-gray-600'
              }`}>PREFERENCES</h2>
              <button
                className={`p-1 rounded transition-colors ${
                  isDarkMode
                    ? 'text-gray-400 hover:bg-gray-700 hover:text-gray-200'
                    : 'text-gray-600 hover:bg-gray-200 hover:text-gray-900'
                }`}
                onClick={() => setIsPreferencesModalOpen(true)}
                aria-label="Edit preferences"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {userPreferences.length > 0 ? (
                userPreferences.map((preference) => (
                  <div
                    key={preference}
                    className="px-4 py-2 bg-amber-700 text-white rounded-full text-sm font-medium"
                  >
                    {preference}
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-sm italic">
                  No preferences set. Click Edit to add some.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Recommendations - Only show when there are recommendations or loading */}
        {(recommendations.length > 0 || isLoading) && (
          <div>
            <h2 className={`text-sm mb-4 uppercase font-medium transition-colors ${
              isDarkMode ? 'text-gray-400' : 'text-gray-600'
            }`}>RECOMMENDATIONS</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {isLoading ? (
                // Show loading skeletons while fetching recommendations
                <>
                  <RecommendationCardSkeleton />
                  <RecommendationCardSkeleton />
                  <RecommendationCardSkeleton />
                </>
              ) : (
                // Show actual recommendations
                recommendations.map((item) => (
                  <RecommendationCard
                    key={item.id}
                    name={item.name}
                    imageUrl={item.imageUrl}
                    onCook={() => console.log('Cook:', item.name)}
                  />
                ))
              )}
            </div>
          </div>
        )}
      </main>

      {/* Preferences Modal */}
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
