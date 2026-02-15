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
          <div key={item.id} className="bg-gray-100 rounded-2xl p-8 h-64 flex items-end cursor-pointer hover:shadow-lg transition-shadow">
            <div className="flex items-center justify-between w-full">
              <span className="text-xl">{item.name}</span>
              <button className="relative w-12 h-12 rounded-full bg-[#212121] flex items-center justify-center text-white hover:bg-[#AF431D] hover:shadow-lg hover:scale-110 transition-all duration-300 ease-out group overflow-hidden">
                <span className="absolute inset-0 rounded-full bg-[#AF431D] opacity-0 group-hover:opacity-30 group-hover:scale-150 transition-all duration-500 ease-out"></span>
                <svg className="w-6 h-6 relative z-10" fill="currentColor" viewBox="0 0 24 24">
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
