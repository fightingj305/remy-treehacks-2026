'use client';

export default function Sidebar() {
  return (
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
  );
}
