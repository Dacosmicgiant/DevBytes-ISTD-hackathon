// frontend/src/services/socket-service.js
import { io } from 'socket.io-client';

// Create socket instance
export const socket = io('http://localhost:5000', {
  autoConnect: false,
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: 5
});

// Add event listeners for connection status
socket.on('connect', () => {
  console.log('Connected to server');
});

socket.on('disconnect', () => {
  console.log('Disconnected from server');
});

socket.on('error', (error) => {
  console.error('Socket error:', error);
});

// Export helper functions
export const sendPoseUpdate = (data) => {
  if (socket.connected) {
    socket.emit('pose_update', data);
  }
};

export const disconnect = () => {
  socket.disconnect();
};

export const connect = () => {
  socket.connect();
};