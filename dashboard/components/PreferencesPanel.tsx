'use client';

interface Preference {
  id: number;
  label: string;
}

interface PreferencesPanelProps {
  preferences?: Preference[];
  onEdit?: () => void;
}

export default function PreferencesPanel({ preferences, onEdit }: PreferencesPanelProps) {
  const defaultPreferences = [
    { id: 1, label: 'Low Sugar' },
    { id: 2, label: 'Low Sodium' },
    { id: 3, label: 'Medium Rare' },
  ];

  const items = preferences || defaultPreferences;

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-medium">Preferences</h2>
        <button
          className="text-gray-600 hover:text-gray-900 transition-colors"
          onClick={onEdit}
        >
          Edit
        </button>
      </div>
      <div className="grid grid-cols-3 gap-6">
        {items.map((item) => (
          <div
            key={item.id}
            className="bg-gray-100 rounded-2xl p-8 h-40 flex items-center justify-center hover:bg-gray-200 hover:shadow-lg transition-all cursor-pointer"
          >
            <span className="text-xl">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
