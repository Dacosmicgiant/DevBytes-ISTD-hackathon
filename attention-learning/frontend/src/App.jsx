// frontend/src/App.jsx
import React from 'react';
import VideoPlayer from './components/VideoPlayer';

function App() {
  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="container mx-auto px-4">
        <h1 className="text-3xl font-bold text-center mb-8">
          Attention-Based Learning Platform
        </h1>
        <VideoPlayer />
      </div>
    </div>
  );
}

export default App;