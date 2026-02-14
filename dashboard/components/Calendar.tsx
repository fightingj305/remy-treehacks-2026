'use client';

import { useState } from 'react';

interface CalendarProps {
  highlightedDates?: number[];
  onDateClick?: (date: number) => void;
}

export default function Calendar({ highlightedDates = [9, 13], onDateClick }: CalendarProps) {
  const [selectedMonth, setSelectedMonth] = useState('Sep');

  const weekDays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  const daysInMonth = Array.from({ length: 30 }, (_, i) => i + 1);

  const handlePrevMonth = () => {
    // Add logic to change month
  };

  const handleNextMonth = () => {
    // Add logic to change month
  };

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <button
          className="text-gray-400 hover:text-gray-600 transition-colors"
          onClick={handlePrevMonth}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <select
          className="bg-transparent border-none text-center focus:outline-none"
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(e.target.value)}
        >
          <option>Jan</option>
          <option>Feb</option>
          <option>Mar</option>
          <option>Apr</option>
          <option>May</option>
          <option>Jun</option>
          <option>Jul</option>
          <option>Aug</option>
          <option>Sep</option>
          <option>Oct</option>
          <option>Nov</option>
          <option>Dec</option>
        </select>
        <button
          className="text-gray-400 hover:text-gray-600 transition-colors"
          onClick={handleNextMonth}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-2 text-center text-sm">
        {weekDays.map((day) => (
          <div key={day} className="text-gray-400 py-2">
            {day}
          </div>
        ))}
        {daysInMonth.map((day) => (
          <button
            key={day}
            className={`py-2 rounded-lg transition-colors ${
              highlightedDates.includes(day)
                ? 'bg-gray-900 text-white'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
            onClick={() => onDateClick?.(day)}
          >
            {day}
          </button>
        ))}
      </div>
    </div>
  );
}
