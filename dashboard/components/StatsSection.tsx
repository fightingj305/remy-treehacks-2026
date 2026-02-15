'use client';

interface Stat {
  id: number;
  label: string;
  value?: string | number;
}

interface StatsSectionProps {
  stats?: Stat[];
  period?: string;
}

export default function StatsSection({ stats, period = 'February' }: StatsSectionProps) {
  const defaultStats: Stat[] = [
    { id: 1, label: 'Avg. Calorie Intake' },
    { id: 2, label: 'Food Waste Reduction' },
  ];

  const items = stats || defaultStats;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-medium">Statistics</h2>
        <span className="text-gray-600">{period}</span>
      </div>
      <div className="grid grid-cols-2 gap-6">
        {items.map((item) => (
          <div
            key={item.id}
            className="bg-gray-100 rounded-2xl p-8 h-64 flex items-center justify-center hover:bg-gray-200 hover:shadow-lg transition-all cursor-pointer"
          >
            <div className="text-center">
              <span className="text-xl block">{item.label}</span>
              {item.value && (
                <span className="text-3xl font-semibold block mt-4">{item.value}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
