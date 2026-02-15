'use client';

interface PreferencesPanelProps {
  preferences?: string[];
  onEdit?: () => void;
}

export default function PreferencesPanel({ preferences = [], onEdit }: PreferencesPanelProps) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-medium">Preferences</h2>
        <button
          className="px-6 py-2 rounded-lg text-gray-600 hover:bg-gray-200 hover:text-gray-900 transition-colors"
          onClick={onEdit}
        >
          Edit
        </button>
      </div>
      <div className="flex flex-wrap gap-3">
        {preferences.length > 0 ? (
          preferences.map((preference) => (
            <div
              key={preference}
              className="px-6 py-3 bg-amber-700 text-white rounded-full text-base font-medium"
            >
              {preference}
            </div>
          ))
        ) : (
          <p className="text-gray-500 italic">No preferences set. Click "edit" to add some.</p>
        )}
      </div>
    </div>
  );
}
