# IRIS AI — Frontend Developer & UI Guide

This document details the frontend architecture, state management with Zustand, and layout hierarchies.

---

## 1. Global State Management (Zustand)

Instead of using prop-drilling or complex Redux templates, we use **Zustand** for lightweight, atomic state management. We maintain two stores:

### A. `useAuthStore.ts`
- **Purpose:** Tracks current user JWT sessions, login/register loading states, Google OAuth authentication flow, and system AI settings.
- **Key Methods:** `login()`, `logout()`, `loginWithGoogle()`, `verifyPin()`, `setupPin()`, `fetchSettings()`, and `updateGeminiKey()`.
- **Session Persistence:** Saves `access_token` in localStorage to persist logins across browser reloads.

### B. `useVaultStore.ts`
- **Purpose:** Manages document arrays, upload actions, dashboard analytics caching, Knowledge Graph nodes, and document re-extraction commands.
- **Key Methods:** `fetchDocuments()`, `uploadDocument()`, `deleteDocument()`, `reextractDocument()`, and `fetchGraph()`.

---

## 2. Layout & Route Mapping

The page layout is structured inside `App.tsx`:
1. **Unauthenticated:** If `isAuthenticated` is false, only the `<Login />` card (with Google Sign-In support) is rendered.
2. **Authenticated:** If true, the layout splits:
   - **Left Panel:** Sidebar component showing brand name, navigation routes, and the Smart Folder tree structure.
   - **Right Panel:** Main container displaying the matching route component:
     - `/dashboard` -> Analytics charts, alerts list, timelines.
     - `/vault` -> Document grid browser.
     - `/graph` -> React Flow visual network.
     - `/chat` -> AI Assistant bubble container.
     - `/upload` -> Drag-drop file area.
     - `/settings` -> Dynamic Gemini API key management (with live test probe), PIN settings, & audit tables.
