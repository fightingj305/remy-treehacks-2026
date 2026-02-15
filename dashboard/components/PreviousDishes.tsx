'use client';

import Calendar from './Calendar';

interface Dish {
  id: number;
  name: string;
  imageUrl?: string;
}

interface PreviousDishesProps {
  dishes?: Dish[];
}

export default function PreviousDishes({ dishes }: PreviousDishesProps) {

  const defaultDishes = [
    {
      id: 1,
      name: 'Spaghetti',
      imageUrl: '/images/dishes/spaghetti.png',
    },
    {
      id: 2,
      name: 'Egg Spam Fried Rice',
      imageUrl: '/images/dishes/egg-veggie-bowl.png',
    },
    {
      id: 3,
      name: 'KBBQ Beef',
      imageUrl: '/images/dishes/kbbq-beef.png',
    },
  ];

  const items = dishes || defaultDishes;

  return (
    <aside className="w-96 border-l border-gray-200 p-8 bg-white">
      <h2 className="text-2xl font-medium mb-6">Previous Dishes</h2>

      {/* Calendar */}
      <Calendar />

      {/* Meal Cards */}
      <div className="space-y-4">
        {items.map((dish) => (
          <div
            key={dish.id}
            className="rounded-2xl overflow-hidden cursor-pointer transition-all hover:shadow-lg"
          >
            <div
              className="h-32 relative flex items-center justify-center"
              style={{
                backgroundImage: dish.imageUrl ? `url(${dish.imageUrl})` : 'none',
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundColor: '#ccc',
              }}
            >
              {/* Progressive blur overlay */}
              <div
                className="absolute inset-0"
                style={{
                  backdropFilter: 'blur(6px)',
                  WebkitBackdropFilter: 'blur(6px)',
                  maskImage: 'linear-gradient(to bottom, rgba(0, 0, 0, 1), rgba(0, 0, 0, 0))',
                  WebkitMaskImage: 'linear-gradient(to bottom, rgba(0, 0, 0, 1), rgba(0, 0, 0, 0))',
                }}
              ></div>

              {/* Dark gradient overlay for text readability */}
              <div
                className="absolute inset-0"
                style={{
                  background: 'linear-gradient(to bottom, rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.3))',
                }}
              ></div>

              {/* Meal name */}
              <h3 className="relative z-10 text-white text-xl font-medium text-center px-4">
                {dish.name}
              </h3>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
