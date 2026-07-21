# IRIS Frontend — React + TypeScript + Vite

The frontend interface for IRIS (NeuroVault) built with React 18, Vite, TypeScript, Tailwind CSS, and Zustand.

---

## 🎨 Key Features & Architecture

- **Login & Authentication (`Login.tsx`)**: Traditional email/password auth + Google OAuth 2.0 integration with dynamic script loading and ID token backend verification.
- **Document Vault (`Vault.tsx`)**: Multi-user isolated document management, PIN lock, search, filtering, grid/table toggle, and document re-extraction dispatch.
- **AI Chat Assistant (`Chat.tsx`)**: Multi-turn conversation UI with document citations, vector store MMR context retrieval, and local rule / Gemini LLM routing.
- **Dashboard (`Dashboard.tsx`)**: Analytics overview, vault health score, category distribution, academic timeline, and document expiry warnings.
- **Knowledge Graph (`Graph.tsx`)**: Visual interactive entity relationship graph using React Flow.
- **Settings Page (`Settings.tsx`)**: System AI engine configuration view allowing users to enter, test, and save custom Gemini API keys via backend live probe endpoint (`POST /api/auth/settings/gemini-key`).

---

## 🛠️ State Management & Stores (`src/store/`)

- `useAuthStore.ts`: Handles user authentication state, token refresh, Google OAuth login flow, and settings API key dispatch.
- `useVaultStore.ts`: Manages document listing, filtering, PIN authentication state, upload pipeline status, and `/reextract` commands.
- `useChatStore.ts`: Stores active chat sessions, turn history, and query citations.

---

## 🚀 Running Locally

```bash
# Install dependencies
npm install

# Start Vite dev server
npm run dev

# Build production bundle
npm run build
```
