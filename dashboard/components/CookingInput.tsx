'use client';

import { useState, useEffect } from 'react';

interface CookingInputProps {
  isDarkMode: boolean;
  userPreferences: string[];
  isLoading: boolean;
  onSubmit: (input: string) => void;
  onOpenPreferences: () => void;
}

const PROMPTS = [
  "I want to cook a high-protein meal with chicken and vegetables",
  "I want to cook something vegan using whatever's in season right now",
  "I want to cook a keto-friendly dinner that's under 30 minutes",
  "I want to cook a traditional Korean dish but make it halal",
  "I want to cook a low-sodium Mediterranean seafood pasta for two"
];

export default function CookingInput({
  isDarkMode,
  userPreferences,
  isLoading,
  onSubmit,
  onOpenPreferences,
}: CookingInputProps) {
  const [userInput, setUserInput] = useState('');
  const [placeholderText, setPlaceholderText] = useState('');
  const [currentPromptIndex, setCurrentPromptIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(true);
  const [charIndex, setCharIndex] = useState(0);

  useEffect(() => {
    if (userInput !== '') {
      setPlaceholderText('');
      return;
    }

    const currentPrompt = PROMPTS[currentPromptIndex];

    if (isTyping) {
      if (charIndex <= currentPrompt.length) {
        const timeout = setTimeout(() => {
          setPlaceholderText(currentPrompt.substring(0, charIndex));
          setCharIndex(charIndex + 1);
        }, 50);
        return () => clearTimeout(timeout);
      } else {
        const pauseTimeout = setTimeout(() => {
          setIsTyping(false);
        }, 2000);
        return () => clearTimeout(pauseTimeout);
      }
    } else {
      if (charIndex > 0) {
        const timeout = setTimeout(() => {
          setPlaceholderText(currentPrompt.substring(0, charIndex - 1));
          setCharIndex(charIndex - 1);
        }, 30);
        return () => clearTimeout(timeout);
      } else {
        setCurrentPromptIndex((prev) => (prev + 1) % PROMPTS.length);
        setIsTyping(true);
        setCharIndex(0);
      }
    }
  }, [currentPromptIndex, isTyping, userInput, charIndex]);

  const handleSubmit = () => {
    if (!userInput.trim() || isLoading) return;
    onSubmit(userInput);
    setUserInput('');
  };

  return (
    <div
      className={`rounded-2xl p-6 shadow-sm border mb-8 transition-colors ${
        isDarkMode ? '#323231ff' : 'border-gray-200'
      }`}
      style={{
        backgroundColor: isDarkMode ? '#3232316d' : 'white',
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
              height: 'calc(1.5rem * 1.5 * 2)',
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
            onClick={onOpenPreferences}
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
  );
}
