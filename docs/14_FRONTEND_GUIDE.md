# NeuroVault AI — Frontend Developer & UI Guide

This document details the frontend architecture, state management with Zustand, and layout hierarchies.

---

## 1. Global State Management (Zustand)

Instead of using prop-drilling or complex Redux templates, we use **Zustand** for lightweight, atomic state management. We maintain two stores:

### A. `useAuthStore.ts`
- **Purpose:** Tracks current user JWT sessions, login/register loading states, and secondary PIN validation sessions.
- **Key Methods:** `login()`, `logout()`, `verifyPin()`, and `setupPin()`.
- **Session Persistence:** Saves `access_token` in localStorage to persist logins across browser reloads.

### B. `useVaultStore.ts`
- **Purpose:** Manages document arrays, upload actions, dashboard analytics caching, and Knowledge Graph nodes.
- **Key Methods:** `fetchDocuments()`, `uploadDocument()`, `deleteDocument()`, and `fetchGraph()`.

---

## 2. Layout & Route Mapping

The page layout is structured inside `App.tsx`:
1. **Unauthenticated:** If `isAuthenticated` is false, only the `<Login />` card is rendered.
2. **Authenticated:** If true, the layout splits:
   - **Left Panel:** Sidebar component showing brand name, navigation routes, and the Smart Folder tree structure.
   - **Right Panel:** Main container displaying the matching route component:
     - `/dashboard` -> Analytics charts, alerts list, timelines.
     - `/vault` -> Document grid browser.
     - `/graph` -> React Flow visual network.
     - `/chat` -> AI Assistant bubble container.
     - `/upload` -> Drag-drop file area.
     - `/settings` -> PIN settings & audit tables.
