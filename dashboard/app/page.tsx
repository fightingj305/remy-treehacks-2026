'use client';

import { useState } from 'react';
import PreferencesModal from '@/components/PreferencesModal';

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
    'Low Sugar',
    'Low Sodium',
    'Medium Rare'
  ]);
  const [userInput, setUserInput] = useState('');

  const recommendations: Recommendation[] = [
    { id: 1, name: 'Spaghetti', imageUrl: '/images/dishes/spaghetti.png' },
    { id: 2, name: 'Spaghetti', imageUrl: '/images/dishes/spaghetti.png' },
    { id: 3, name: 'Spaghetti', imageUrl: '/images/dishes/spaghetti.png' },
  ];

  const handleSavePreferences = (preferences: string[]) => {
    setUserPreferences(preferences);
    // TODO: Send preferences to AI backend
    console.log('Saved preferences:', preferences);
  };

  const handleSubmit = () => {
    // TODO: Send user input to AI backend
    console.log('User input:', userInput);
  };

  const handleVoiceInput = () => {
    // TODO: Implement voice input
    console.log('Voice input activated');
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Main Content */}
      <main
        className={`flex-1 p-12 transition-all duration-300 flex flex-col justify-center ${
          isSidebarOpen ? 'max-w-4xl' : 'max-w-4xl mx-auto'
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
        <p className="text-gray-600 mb-2 text-lg">Good evening, Allen</p>
        <h1 className="text-4xl font-semibold mb-8">
          What do you wish to cook for dinner today?
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
                <div className="absolute inset-0 flex items-center pointer-events-none">
                  <span className="text-lg text-gray-400">
                    I want to cook <span className="animate-blink">|</span>
                  </span>
                </div>
              )}
              <input
                type="text"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                className="w-full text-lg text-black outline-none bg-transparent"
              />
            </div>

            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              className="text-white p-3 rounded-full transition-colors"
              style={{ backgroundColor: '#AF431D' }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#8A3517'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#AF431D'}
            >
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

      {/* Right Sidebar */}
      <aside
        className={`bg-white border-l border-gray-200 transition-all duration-300 relative ${
          isSidebarOpen ? 'w-96' : 'w-0 overflow-hidden'
        }`}
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
                    {recommendations.map((item) => (
                      <div
                        key={item.id}
                        className="rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 hover:shadow-xl relative group"
                      >
                        <div
                          className="h-32 relative flex items-end justify-between p-4"
                          style={{
                            backgroundImage: `url(${item.imageUrl})`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                            backgroundColor: '#ccc',
                          }}
                        >
                          {/* Progressive blur overlay */}
                          <div
                            className="absolute inset-0"
                            style={{
                              backdropFilter: 'blur(4px)',
                              WebkitBackdropFilter: 'blur(4px)',
                              maskImage:
                                'linear-gradient(to top, rgba(0, 0, 0, 1), rgba(0, 0, 0, 0))',
                              WebkitMaskImage:
                                'linear-gradient(to top, rgba(0, 0, 0, 1), rgba(0, 0, 0, 0))',
                            }}
                          ></div>

                          {/* Dark gradient overlay */}
                          <div
                            className="absolute inset-0"
                            style={{
                              background:
                                'linear-gradient(to top, rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.3))',
                            }}
                          ></div>

                          {/* Hover overlay - darker backdrop */}
                          <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-20 transition-opacity duration-300"></div>

                          {/* Meal name */}
                          <h3 className="relative z-10 text-white text-lg font-medium">
                            {item.name}
                          </h3>

                          {/* Cook button */}
                          <button className="relative z-10 flex flex-col items-center gap-1 transition-transform duration-300 group-hover:-translate-y-2 group-hover:scale-110">
                            <div className="bg-black p-2 rounded-full hover:bg-gray-900 transition-all">
                              <svg
                                width="20"
                                height="20"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="white"
                                strokeWidth="2"
                              >
                                <circle cx="12" cy="12" r="10" />
                                <path d="M12 16V8M8 12l4-4 4 4" />
                              </svg>
                            </div>
                            <span className="text-white text-sm font-medium">Cook</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </aside>

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
