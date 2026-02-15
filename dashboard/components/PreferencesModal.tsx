'use client';

import { useState } from 'react';

interface PreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (selectedPreferences: string[]) => void;
  initialPreferences?: string[];
  isDarkMode?: boolean;
}

const PREFERENCE_CATEGORIES = {
  'diet types': [
    'Vegan', 'Vegetarian', 'Pescatarian', 'Keto', 'Paleo', 'Mediterranean',
    'Whole30', 'Carnivore', 'Raw Food', 'Flexitarian', 'DASH', 'Low FODMAP'
  ],
  'allergies & intolerances': [
    'Gluten Free', 'Dairy Free', 'Nut Free', 'Soy Free', 'Egg Free',
    'Shellfish Free', 'Sesame Free', 'Lactose Free', 'Corn Free', 'Nightshade Free'
  ],
  'nutritional goals': [
    'Low Sugar', 'Low Sodium', 'Low Carb', 'High Protein', 'Low Fat',
    'High Fiber', 'Low Calorie', 'Low Cholesterol', 'Iron Rich', 'Calcium Rich'
  ],
  'religious & cultural': [
    'Halal', 'Kosher', 'No Pork', 'No Beef', 'No Alcohol in Cooking',
    'Jain Vegetarian', 'Sattvic'
  ],
  'cooking preferences': [
    'Medium Rare', 'Well Done', 'No Spicy', 'Mild Heat', 'No Raw Fish',
    'No Fried Foods', 'Oil Free', 'Air Fryer Only', 'One Pot Meals', 'Under 30 Minutes'
  ]
};

export default function PreferencesModal({
  isOpen,
  onClose,
  onSave,
  initialPreferences = [],
  isDarkMode = false
}: PreferencesModalProps) {
  const [selectedPreferences, setSelectedPreferences] = useState<string[]>(initialPreferences);

  if (!isOpen) return null;

  const togglePreference = (preference: string) => {
    setSelectedPreferences(prev =>
      prev.includes(preference)
        ? prev.filter(p => p !== preference)
        : [...prev, preference]
    );
  };

  const handleSave = () => {
    onSave(selectedPreferences);
    onClose();
  };

  const handleClearAll = () => {
    setSelectedPreferences([]);
  };

  return (
    <>
      {/* Backdrop - Click to dismiss */}
      <div
        className="fixed inset-0 z-40"
        style={{ backgroundColor: isDarkMode ? 'rgba(0, 0, 0, 0.6)' : 'rgba(0, 0, 0, 0.24)' }}
        onClick={onClose}
      ></div>

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-none">
        <div
          className="rounded-3xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto pointer-events-auto transition-colors"
          style={{
            backgroundColor: isDarkMode ? '#2f2f2a' : 'white',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className={`sticky top-0 border-b px-8 py-6 flex items-center justify-between rounded-t-3xl transition-colors ${
              isDarkMode ? 'border-gray-700' : 'border-gray-200'
            }`}
            style={{
              backgroundColor: isDarkMode ? '#2f2f2a' : 'white',
            }}
          >
            <h2 className={`text-3xl font-semibold transition-colors ${
              isDarkMode ? 'text-white' : 'text-gray-900'
            }`}>Preferences</h2>
            <button
              onClick={onClose}
              className={`transition-colors ${
                isDarkMode
                  ? 'text-gray-400 hover:text-gray-200'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="px-8 py-6 space-y-8">
            {Object.entries(PREFERENCE_CATEGORIES).map(([category, options]) => (
              <div key={category}>
                <h3 className={`text-lg mb-4 transition-colors ${
                  isDarkMode ? 'text-amber-500' : 'text-amber-800'
                }`}>{category}</h3>
                <div className="flex flex-wrap gap-3">
                  {options.map(option => (
                    <button
                      key={option}
                      onClick={() => togglePreference(option)}
                      className={`px-6 py-3 rounded-full text-base font-medium transition-all ${
                        selectedPreferences.includes(option)
                          ? 'bg-amber-700 text-white hover:bg-amber-800'
                          : isDarkMode
                            ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                            : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                      }`}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div
            className={`sticky bottom-0 border-t px-8 py-6 flex items-center justify-between rounded-b-3xl transition-colors ${
              isDarkMode ? 'border-gray-700' : 'border-gray-200'
            }`}
            style={{
              backgroundColor: isDarkMode ? '#2f2f2a' : 'white',
            }}
          >
            <button
              onClick={handleClearAll}
              className={`font-medium transition-colors ${
                isDarkMode
                  ? 'text-red-400 hover:text-red-300'
                  : 'text-red-600 hover:text-red-800'
              }`}
            >
              Clear All Filters
            </button>
            <div className="flex gap-4">
              <button
                onClick={onClose}
                className={`px-6 py-3 font-medium transition-colors ${
                  isDarkMode
                    ? 'text-gray-300 hover:text-gray-100'
                    : 'text-gray-700 hover:text-gray-900'
                }`}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-8 py-3 text-white rounded-full font-medium transition-colors bg-amber-700 hover:bg-amber-800"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
