# TransferSession Full-Stack Backend Service

Autonomously engineered by the **SYNTRA Multi-Agent Engineering Organization**.

## System Overview
- **Framework**: FastAPI (async ASGI)
- **Database**: SQLite (aiosqlite driver) with SQLAlchemy 2.0 ORM
- **Validation**: Pydantic v2 schemas
- **Test Runner**: Pytest + pytest-asyncio + HTTPX ASGITransport
- **Mission Objective**: Help me design and architect a secure, end-to-end Peer-to-Peer (P2P) WebRTC Data Transfer Web Application. The core user loop must be incredibly simple: User A generates a unique 6-digit numeric room code, User B enters that code, a direct P2P data channel is established, and they can securely transfer files, text, or stream media directly with zero cloud storage footprint. Please structure your response into the following comprehensive, production-ready modules: ### 1. System Architecture & The Signaling Protocol Detail the underlying infrastructure and connection handshake lifecycle: - **Signaling Server Architecture:** Recommend the best technology stack (e.g., Node.js + WebSockets, Socket.io, or Go) to manage the initial connection without handling actual file payload data. - **6-Digit Code Lifecycle:** Explain the database/memory caching architecture (e.g., Redis) required to generate, validate, expire (e.g., 5-minute TTL), and map 6-digit collision-resistant room codes to specific WebSocket session IDs. - **NAT Traversal Network Strategy:** Outline the STUN/TURN server strategy (including open-source options like Coturn) to handle symmetric NATs and firewalls, ensuring a 99%+ connection success rate. - **WebRTC Connection Lifecycle:** Provide a step-by-step breakdown of the sequence (Offer, Answer, ICE Candidates) mapping exactly how User A and User B connect using only the 6-digit code. ### 2. P2P Data Transfer & Security Engine Detail how files are handled safely and reliably inside the browser: - **Chunking & Buffer Management:** Explain how to slice large files (e.g., >1GB) into binary ArrayBuffers, transmit them across the WebRTC `RTCDataChannel`, and reassemble them in the recipient's browser using the FileSystem Writable File Stream API. - **Flow Control & Congestion Management:** Describe how to monitor `bufferedAmount` and adjust chunk transmission speeds dynamically to prevent browser tab crashes. - **Security & Privacy:** Highlight the cryptographic measures (DTLS/SRTP encryption) native to WebRTC, and confirm how to guarantee zero-knowledge architecture (no file data ever touches a server). ### 3. UI/UX Design System & User Journeys Provide a highly scannable, modern, and high-converting frontend layout specification. Use a sleek, minimalist, dark-themed SaaS aesthetic (inspired by Linear or Vercel). Outline the visual layout, components, and animations for: - **Landing / Initial State:** Split view or toggle. Left/Top: "Send" button that generates a prominent, highly readable 6-digit code with a "Copy Link" shortcut. Right/Bottom: A clean, auto-focused numeric input field for "Receive" where typing the 6th digit automatically initiates the connection handshake. - **The Transfer Dashboard (Connected State):** - A beautiful, minimalist drag-and-drop file dropzone featuring subtle micro-animations (e.g., border pulse on file hover). - A real-time file queue panel showing file name, format icon, size, and individual progress bars. - A metrics display panel showing Peer Connection Status, Current Transfer Speed (MB/s), and Estimated Time Remaining (ETA). - **Global UI States:** Clear component wireframes/descriptions for Success/Completion states, Connection Loss/Interrupted errors, and Peer Disconnected alerts. ### 4. SaaS Monetization & Tier Infrastructure Design a scalable pricing framework that keeps operational costs low while maximizing profit: - **Free Tier Constraints:** Enforce client-side limitations (e.g., maximum 50MB per file transfer, maximum 2 concurrent transfers, basic transfer speeds). - **Premium/Pro Tier Features:** Propose features that add immense value without breaking the P2P model (e.g., unlimited file sizes, priority TURN server relays for blazing-fast bypass speeds, custom alphanumeric room codes, persistent transfer history logs stored strictly in browser IndexedDB). - **Authentication & Subscription Stack:** Recommend a lightweight SaaS integration strategy (e.g., Clerk or Auth0 for authentication; Stripe for metered or tiered billing checks via lightweight JWT tokens passed during the WebSocket handshake). ### 5. Production Technology Stack Recommendation Provide a definitive, modern tech stack list spanning: - **Frontend Framework:** (e.g., Next.js, React, or Vue.js with Tailwind CSS or Shadcn/ui components). - **WebRTC & State Management Libraries:** (e.g., Zustand, simple-peer, or native WebRTC APIs). - **Backend/Hosting:** (e.g., Vercel for the frontend, AWS/DigitalOcean/Render for the persistent WebSocket signaling and Coturn deployment).

## Quickstart

```bash
# 1. Install dependencies
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pytest pytest-asyncio httpx

# 2. Run the application
uvicorn main:app --reload --port 8000

# 3. Access Swagger OpenAPI Docs
open http://localhost:8000/docs

# 4. Run automated test suite
pytest test_api.py -v
```

## REST API Specification
- `GET /health` — Service health probe
- `GET /api/v1/transfer_sessions` — Search, filter, and paginate records
- `GET /api/v1/transfer_sessions/stats` — Real-time telemetry and aggregation metrics
- `GET /api/v1/transfer_sessions/{id}` — Fetch single record by UUID
- `POST /api/v1/transfer_sessions` — Create a new validated record
- `PUT /api/v1/transfer_sessions/{id}` — Update record
- `DELETE /api/v1/transfer_sessions/{id}` — Delete record
