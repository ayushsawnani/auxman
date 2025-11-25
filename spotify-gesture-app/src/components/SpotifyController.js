import React, { useEffect, useState } from 'react';
import axios from 'axios';

const SpotifyController = () => {
  const [gesture, setGesture] = useState(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get('http://localhost:5000/gesture'); // adjust to your backend URL
        if (response.data.gesture !== gesture) {
          setGesture(response.data.gesture);
          handleGesture(response.data.gesture);
        }
      } catch (err) {
        console.error('Error fetching gesture:', err);
      }
    }, 2000); // poll every 2 seconds

    return () => clearInterval(interval);
  }, [gesture]);

  const handleGesture = (gesture) => {
    switch (gesture) {
      case 'play':
        axios.post('/spotify/play');
        break;
      case 'pause':
        axios.post('/spotify/pause');
        break;
      case 'next':
        axios.post('/spotify/next');
        break;
      case 'like':
        axios.post('/spotify/like');
        break;
      default:
        break;
    }
  };

  return (
    <div>
      <h2>Current Gesture: {gesture}</h2>
    </div>
  );
};

export default SpotifyController;