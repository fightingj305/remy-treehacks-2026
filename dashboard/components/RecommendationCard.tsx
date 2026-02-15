'use client';

import { useState } from 'react';

interface RecommendationCardProps {
  name: string;
  imageUrl: string;
  isPlaying?: boolean;
  onTogglePlay?: () => void;
  onCook?: () => void;
}

const FALLBACK_IMAGE = '/images/dishes/placeholder.png';

export default function RecommendationCard({ name, imageUrl, isPlaying = false, onTogglePlay, onCook }: RecommendationCardProps) {
  const [imgSrc, setImgSrc] = useState(imageUrl);
  const [isImageLoaded, setIsImageLoaded] = useState(false);

  const handleImageError = () => {
    setImgSrc(FALLBACK_IMAGE);
  };

  const handleImageLoad = () => {
    setIsImageLoaded(true);
  };

  return (
    <div className="rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 hover:shadow-xl relative group">
      <div className="h-32 relative flex items-end justify-between p-4 bg-gray-200">
        {/* Background Image */}
        <img
          src={imgSrc}
          alt={name}
          onError={handleImageError}
          onLoad={handleImageLoad}
          className="absolute inset-0 w-full h-full object-cover"
        />

        {/* Loading skeleton overlay */}
        {!isImageLoaded && (
          <div className="absolute inset-0 bg-gray-300 animate-pulse" />
        )}

        {/* Progressive blur overlay */}
        <div
          className="absolute inset-0"
          style={{
            backdropFilter: 'blur(4px)',
            WebkitBackdropFilter: 'blur(4px)',
            maskImage: 'linear-gradient(to top, rgba(0, 0, 0, 1), rgba(0, 0, 0, 0))',
            WebkitMaskImage: 'linear-gradient(to top, rgba(0, 0, 0, 1), rgba(0, 0, 0, 0))',
          }}
        />

        {/* Dark gradient overlay */}
        <div
          className="absolute inset-0"
          style={{
            background: 'linear-gradient(to top, rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.3))',
          }}
        />

        {/* Hover overlay - darker backdrop */}
        <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-20 transition-opacity duration-300" />

        {/* Meal name */}
        <h3 className="relative z-10 text-white text-lg font-medium">
          {name}
        </h3>

        {/* Play/Pause button */}
        <button
          onClick={() => {
            if (onTogglePlay) onTogglePlay();
            if (!isPlaying && onCook) onCook();
          }}
          className="relative z-10 flex flex-col items-center gap-1 transition-transform duration-300 group-hover:-translate-y-2 group-hover:scale-110"
        >
          <div className={`p-2 rounded-full transition-colors ${isPlaying ? 'bg-[#AF431D]' : 'bg-[#333] group-hover:bg-[#AF431D]'}`}>
            {isPlaying ? (
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="white"
                stroke="none"
              >
                <rect x="6" y="4" width="4" height="16" rx="1" />
                <rect x="14" y="4" width="4" height="16" rx="1" />
              </svg>
            ) : (
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="white"
                stroke="none"
              >
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </div>
          <span className="text-white text-sm font-medium">Cook</span>
        </button>
      </div>
    </div>
  );
}

// Loading skeleton component
export function RecommendationCardSkeleton() {
  return (
    <div className="rounded-2xl overflow-hidden">
      <div className="h-32 relative bg-gray-200 animate-pulse">
        <div className="absolute inset-0 flex items-end justify-between p-4">
          {/* Skeleton text */}
          <div className="h-6 w-32 bg-gray-300 rounded" />
          {/* Skeleton button */}
          <div className="h-12 w-12 bg-gray-300 rounded-full" />
        </div>
      </div>
    </div>
  );
}
