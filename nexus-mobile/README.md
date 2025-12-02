# Nexus Mobile

A React Native mobile app for playing Nexus on iOS and Android.

## Features

- Full game parity with web version
- Realtime and correspondence game modes
- Interactive touch-based game board
- Debt resolution and forced unblocking support
- WebSocket for live game updates
- User authentication
- Game lobby with seeks

## Prerequisites

- Node.js 18+
- For iOS: macOS with Xcode 15+ installed
- For Android: Android Studio with SDK 34+

## Setup

1. Install dependencies:
```bash
cd nexus-mobile
npm install
```

2. For iOS, install CocoaPods:
```bash
cd ios
pod install
cd ..
```

3. Configure server URL in `src/api/client.ts`:
   - Android emulator: `http://10.0.2.2:8000` (default)
   - iOS simulator: `http://localhost:8000`
   - Physical device: Use your computer's IP address

## Running

### Android

```bash
# Start Metro bundler
npm start

# In another terminal, run on Android
npm run android
```

### iOS

```bash
# Start Metro bundler
npm start

# In another terminal, run on iOS
npm run ios
```

## Project Structure

```
nexus-mobile/
├── App.tsx                    # Root component
├── index.js                   # Entry point
├── ios/                       # iOS native code (Swift)
│   ├── NexusMobile/
│   ├── NexusMobile.xcodeproj/
│   └── Podfile
├── android/                   # Android native code (Kotlin)
│   ├── app/
│   └── gradle files
├── src/
│   ├── api/client.ts          # API client with WebSocket
│   ├── types/index.ts         # TypeScript interfaces
│   ├── context/
│   │   └── AuthContext.tsx    # Auth state management
│   ├── components/
│   │   └── Board.tsx          # SVG game board
│   ├── navigation/
│   │   └── AppNavigator.tsx   # Tab + Stack navigation
│   └── screens/
│       ├── LoginScreen.tsx
│       ├── RegisterScreen.tsx
│       ├── LobbyScreen.tsx
│       ├── GamesScreen.tsx
│       ├── GameScreen.tsx
│       ├── RulesScreen.tsx
│       └── ProfileScreen.tsx
└── package.json
```

## Backend Server

Make sure the Nexus backend is running:

```bash
cd ../nexus-web/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

### Android Emulator Can't Connect
- Use `http://10.0.2.2:8000` (not localhost)
- Ensure backend runs on `0.0.0.0:8000`

### iOS Simulator Network Issues
- Use `http://localhost:8000` for simulator
- For physical device, use Mac's IP address

### Pod Install Fails
```bash
cd ios
pod deintegrate
pod install
```
