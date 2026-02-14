'use client';

interface Recommendation {
  id: number;
  name: string;
}

interface RecommendationCardsProps {
  recommendations?: Recommendation[];
}

export default function RecommendationCards({ recommendations }: RecommendationCardsProps) {
  const defaultRecommendations = [
    { id: 1, name: 'Meal Name' },
    { id: 2, name: 'Meal Name' },
  ];

  const items = recommendations || defaultRecommendations;

  return (
    <div className="mb-8">
      <h2 className="text-2xl font-medium mb-6">Recommendations</h2>
      <div className="grid grid-cols-2 gap-6">
        {items.map((item) => (
          <div key={item.id} className="bg-gray-100 rounded-2xl p-8 h-64 flex items-end">
            <div className="flex items-center justify-between w-full">
              <span className="text-xl">{item.name}</span>
              <button className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center text-white hover:bg-gray-800 transition-colors">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
