'use client';

import RecommendationCard, { RecommendationCardSkeleton } from '@/components/RecommendationCard';

export interface Recommendation {
  id: number;
  name: string;
  imageUrl: string;
  description: string;
  recipeTaskQueue: string[];
}

interface RecommendationsGridProps {
  recommendations: Recommendation[];
  isLoading: boolean;
  isDarkMode: boolean;
  playingCardId: number | null;
  onTogglePlay: (id: number) => void;
  onCook: (item: Recommendation) => void;
}

export default function RecommendationsGrid({
  recommendations,
  isLoading,
  isDarkMode,
  playingCardId,
  onTogglePlay,
  onCook,
}: RecommendationsGridProps) {
  if (!isLoading && recommendations.length === 0) return null;

  return (
    <div>
      <h2 className={`text-sm mb-4 uppercase font-medium transition-colors ${
        isDarkMode ? 'text-gray-400' : 'text-gray-600'
      }`}>RECOMMENDATIONS</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <>
            <RecommendationCardSkeleton />
            <RecommendationCardSkeleton />
            <RecommendationCardSkeleton />
          </>
        ) : (
          recommendations.map((item) => (
            <RecommendationCard
              key={item.id}
              name={item.name}
              imageUrl={item.imageUrl}
              isPlaying={playingCardId === item.id}
              onTogglePlay={() => onTogglePlay(item.id)}
              onCook={() => onCook(item)}
            />
          ))
        )}
      </div>
    </div>
  );
}
