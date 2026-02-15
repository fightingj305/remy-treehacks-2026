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
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [sidebarAnimationKey, setSidebarAnimationKey] = useState(0);
  const [userPreferences, setUserPreferences] = useState<string[]>([
    'Nut Free',
    'Keto',
    'No Spicy'
  ]);
  const [userInput, setUserInput] = useState('');
  const [recommendations, setRecommendations] = useState<Recommendation[]>([
    { id: 1, name: 'Spaghetti', imageUrl: '/images/dishes/spaghetti.png' },
    { id: 2, name: 'Egg Veggie Bowl', imageUrl: '/images/dishes/egg-veggie-bowl.png' },
    { id: 3, name: 'KBBQ Beef', imageUrl: '/images/dishes/kbbq-beef.png' },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [aiMessage, setAiMessage] = useState('');

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
        throw new Error('Failed to get recommendations');
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
      // TODO: Show error message to user
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceInput = () => {
    // TODO: Implement voice input
    console.log('Voice input activated');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Responsive Container */}
      <div className="flex min-h-screen max-w-[1920px] mx-auto">
        {/* Main Content */}
        <main
          className={`flex-1 px-6 py-12 md:px-12 lg:px-24 xl:px-32 2xl:px-48 transition-all duration-300 flex flex-col justify-center ${
            isSidebarOpen ? '' : 'mx-auto'
          }`}
        >
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <img
            src="/images/logo.png"
            alt="Logo"
            className="object-contain"
            style={{ height: '100px' }}
          />
        </div>

        {/* Greeting */}
        <p className="text-gray-600 mb-2 text-lg">hello Allen</p>
        <h1 className="text-4xl font-semibold mb-8">
          What do you wish to cook?
        </h1>

        {/* Input Box */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 mb-8">
          <div className="flex items-center gap-4">
            {/* Microphone Button */}
            <button
              onClick={handleVoiceInput}
              className="text-gray-500 hover:text-gray-900 transition-colors p-2"
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            </button>

            {/* Text Input */}
            <div className="flex-1 relative">
              {userInput === '' && (
                <div className="absolute top-0 left-0 flex items-start pt-1 pointer-events-none">
                  <span className="text-lg text-gray-400">
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
                className="w-full text-lg text-black outline-none bg-transparent resize-none overflow-y-auto"
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
        </div>
        </main>

        {/* Sidebar Toggle Button (when closed) */}
        {!isSidebarOpen && (
          <button
            onClick={() => {
              setIsSidebarOpen(true);
              setSidebarAnimationKey(prev => prev + 1);
            }}
            className="fixed top-8 right-8 p-3 rounded-full transition-colors z-30 text-gray-600 hover:text-gray-900"
            style={{ backgroundColor: 'transparent' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#E5E5E5'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
        )}

        {/* Mobile Backdrop Overlay */}
        {isSidebarOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-25 z-40 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        {/* Right Sidebar */}
        <aside
          className={`bg-white border-l border-gray-200 transition-all duration-300
            ${isSidebarOpen ? 'fixed md:relative right-0 top-0 h-full w-80 md:w-96 z-50' : 'w-0 overflow-hidden'}
            md:relative md:h-auto`}
        >
        {isSidebarOpen && (
          <>
            {/* Fixed Close Button */}
            <div className="sticky top-0 z-20 bg-white px-8 pt-8">
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="mb-6 p-3 rounded-full transition-colors text-gray-600 hover:text-gray-900"
                style={{ backgroundColor: 'transparent' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#E5E5E5'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="overflow-y-auto px-8 pb-8" style={{ maxHeight: 'calc(100vh - 120px)' }}>
              <div key={sidebarAnimationKey} className="animate-slideInFromRight">
                {/* Preferences */}
                <div className="mb-8">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm text-gray-600 uppercase font-medium">PREFERENCES</h2>
                    <button
                      className="px-4 py-1 rounded-lg text-sm text-gray-600 hover:bg-gray-200 hover:text-gray-900 transition-colors"
                      onClick={() => setIsPreferencesModalOpen(true)}
                    >
                      edit
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

                {/* Recommendations */}
                <div>
                  <h2 className="text-sm text-gray-600 mb-4 uppercase font-medium">RECOMMENDATIONS</h2>
                  <div className="space-y-4">
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
              </div>
            </div>
          </>
        )}
        </aside>
      </div>

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
