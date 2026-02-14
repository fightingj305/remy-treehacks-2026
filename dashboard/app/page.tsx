'use client';

import { useState } from 'react';

export default function Dashboard() {
  const [selectedMonth] = useState('Sep');

  return (
    <div className="flex min-h-screen bg-white">
      {/* Sidebar */}
      <aside className="w-32 flex flex-col items-center py-8 space-y-12 border-r border-gray-200">
        {/* Logo */}
        <div className="w-20 h-20 bg-gradient-to-b from-gray-800 to-orange-800 rounded-full flex items-center justify-center text-white text-2xl">
          <div className="flex flex-col items-center">
            <span>+</span>
            <span className="text-sm">🧑‍🍳</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col items-center space-y-8">
          <button className="flex flex-col items-center gap-2 text-gray-700 hover:text-gray-900">
            <div className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center text-white">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <span className="text-sm">Search</span>
          </button>

          <button className="flex flex-col items-center gap-2 text-gray-700 hover:text-gray-900">
            <div className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center text-white">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <span className="text-sm">Buy</span>
          </button>

          <button className="flex flex-col items-center gap-2 text-gray-700 hover:text-gray-900">
            <div className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center text-white">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </div>
            <span className="text-sm">Saved</span>
          </button>

          <button className="flex flex-col items-center gap-2 text-gray-700 hover:text-gray-900">
            <div className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center text-white">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <span className="text-sm">Settings</span>
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-12">
        {/* Greeting */}
        <div className="mb-12">
          <p className="text-gray-600 mb-2">Good morning, Allen</p>
          <h1 className="text-4xl font-semibold mb-8">What do you wish to cook today?</h1>

          {/* Recommendations */}
          <div className="mb-8">
            <h2 className="text-2xl font-medium mb-6">Recommendations</h2>
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-gray-100 rounded-2xl p-8 h-64 flex items-end">
                <div className="flex items-center justify-between w-full">
                  <span className="text-xl">Meal Name</span>
                  <button className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center text-white">
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="bg-gray-100 rounded-2xl p-8 h-64 flex items-end">
                <div className="flex items-center justify-between w-full">
                  <span className="text-xl">Meal Name</span>
                  <button className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center text-white">
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Preferences */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-medium">Preferences</h2>
              <button className="text-gray-600 hover:text-gray-900">Edit</button>
            </div>
            <div className="grid grid-cols-3 gap-6">
              <div className="bg-gray-100 rounded-2xl p-8 h-40 flex items-center justify-center">
                <span className="text-xl">Low Sugar</span>
              </div>
              <div className="bg-gray-100 rounded-2xl p-8 h-40 flex items-center justify-center">
                <span className="text-xl">Low Sodium</span>
              </div>
              <div className="bg-gray-100 rounded-2xl p-8 h-40 flex items-center justify-center">
                <span className="text-xl">Medium Rare</span>
              </div>
            </div>
          </div>

          {/* Statistics */}
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-medium">Statistics</h2>
              <span className="text-gray-600">February</span>
            </div>
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-gray-100 rounded-2xl p-8 h-64 flex items-center justify-center">
                <span className="text-xl">Avg. Calorie Intake</span>
              </div>
              <div className="bg-gray-100 rounded-2xl p-8 h-64 flex items-center justify-center">
                <span className="text-xl">Food Waste Reduction</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Right Sidebar - Previous Dishes */}
      <aside className="w-96 border-l border-gray-200 p-8">
        <h2 className="text-2xl font-medium mb-6">Previous Dishes</h2>

        {/* Calendar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <button className="text-gray-400 hover:text-gray-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <select className="bg-transparent border-none text-center" value={selectedMonth}>
              <option>Sep</option>
            </select>
            <button className="text-gray-400 hover:text-gray-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-2 text-center text-sm">
            <div className="text-gray-400 py-2">Su</div>
            <div className="text-gray-400 py-2">Mo</div>
            <div className="text-gray-400 py-2">Tu</div>
            <div className="text-gray-400 py-2">We</div>
            <div className="text-gray-400 py-2">Th</div>
            <div className="text-gray-400 py-2">Fr</div>
            <div className="text-gray-400 py-2">Sa</div>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30].map((day, idx) => (
              <div
                key={day}
                className={`py-2 rounded-lg ${
                  day === 9 || day === 13
                    ? 'bg-gray-900 text-white'
                    : day > 30
                    ? 'text-gray-300'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                {day > 30 ? day - 30 : day}
              </div>
            ))}
          </div>
        </div>

        {/* Meal Cards */}
        <div className="space-y-4">
          <div className="rounded-2xl overflow-hidden">
            <div className="h-32 bg-gradient-to-r from-orange-400 to-orange-600 flex items-center justify-center text-white text-2xl font-medium">
              Spaghetti
            </div>
            <div className="p-4 bg-gray-50">
              <p className="text-sm text-gray-600">Dietary limitations</p>
            </div>
          </div>

          <div className="rounded-2xl overflow-hidden">
            <div className="h-32 bg-gradient-to-r from-gray-400 to-gray-600 flex items-center justify-center text-white text-2xl font-medium">
              Meal Name
            </div>
            <div className="p-4 bg-gray-50">
              <p className="text-sm text-gray-600">Dietary limitations</p>
            </div>
          </div>

          <div className="rounded-2xl overflow-hidden">
            <div className="h-32 bg-gradient-to-r from-orange-700 to-red-900 flex items-center justify-center text-white text-2xl font-medium">
              Meal Name
            </div>
            <div className="p-4 bg-gray-50">
              <p className="text-sm text-gray-600">Dietary limitations</p>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
