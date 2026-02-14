'use client';

import Calendar from './Calendar';

interface Dish {
  id: number;
  name: string;
  dietaryLimitations?: string;
  gradientFrom: string;
  gradientTo: string;
}

interface PreviousDishesProps {
  dishes?: Dish[];
}

export default function PreviousDishes({ dishes }: PreviousDishesProps) {
  const defaultDishes = [
    {
      id: 1,
      name: 'Spaghetti',
      dietaryLimitations: 'Dietary limitations',
      gradientFrom: 'orange-400',
      gradientTo: 'orange-600',
    },
    {
      id: 2,
      name: 'Meal Name',
      dietaryLimitations: 'Dietary limitations',
      gradientFrom: 'gray-400',
      gradientTo: 'gray-600',
    },
    {
      id: 3,
      name: 'Meal Name',
      dietaryLimitations: 'Dietary limitations',
      gradientFrom: 'orange-700',
      gradientTo: 'red-900',
    },
  ];

  const items = dishes || defaultDishes;

  return (
    <aside className="w-96 border-l border-gray-200 p-8">
      <h2 className="text-2xl font-medium mb-6">Previous Dishes</h2>

      {/* Calendar */}
      <Calendar />

      {/* Meal Cards */}
      <div className="space-y-4">
        {items.map((dish) => (
          <div key={dish.id} className="rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
            <div
              className={`h-32 bg-gradient-to-r from-${dish.gradientFrom} to-${dish.gradientTo} flex items-center justify-center text-white text-2xl font-medium`}
            >
              {dish.name}
            </div>
            <div className="p-4 bg-gray-50">
              <p className="text-sm text-gray-600">{dish.dietaryLimitations}</p>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
