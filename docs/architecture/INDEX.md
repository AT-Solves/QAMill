# Architecture Documentation Index

Design documents, architecture plans, and technical specifications.

## Contents

| Document | Purpose |
|----------|---------|
| [ENTERPRISE_REFACTOR_PLAN.md](./ENTERPRISE_REFACTOR_PLAN.md) | Enterprise architecture refactoring strategy |
| [REFACTOR_SUMMARY.md](./REFACTOR_SUMMARY.md) | Summary of refactoring work |
| [IMPLEMENTATION_AUDIT.md](./IMPLEMENTATION_AUDIT.md) | Complete implementation audit |
| [PHASE4_SUMMARY.md](./PHASE4_SUMMARY.md) | Phase 4 implementation details |
| [PHASE6_WEBSOCKET.md](./PHASE6_WEBSOCKET.md) | WebSocket integration and real-time features |
| [MULTI_LANGUAGE_ROADMAP.md](./MULTI_LANGUAGE_ROADMAP.md) | Multi-language support roadmap |
| [HANDOFF.md](./HANDOFF.md) | Project handoff documentation |

## System Architecture

### Core Components
- **Mutation Testing Engine** - 17+ operators for Python & JavaScript
- **AI-Powered Test Generation** - 8 LLM providers
- **Gap Analysis** - Untested code detection
- **Compliance Management** - 8 compliance standards

### Services (9 Total)
1. Mutation Engine
2. Test Generation
3. Gap Analysis
4. Compliance Service
5. LLM Provider Manager
6. OAuth Extended Service
7. Email Distribution
8. Executive Dashboard
9. Team/Organization Service

### Data Model
- Multi-tenant architecture with organization & team hierarchies
- Role-based access control (4-level hierarchy)
- Secure invitation system with 7-day expiry
- Project isolation and sharing

---

## Reading Guide

**First Time?**
1. Read [ENTERPRISE_REFACTOR_PLAN.md](./ENTERPRISE_REFACTOR_PLAN.md) for overview
2. Check [IMPLEMENTATION_AUDIT.md](./IMPLEMENTATION_AUDIT.md) for completeness
3. Review [PHASE4_SUMMARY.md](./PHASE4_SUMMARY.md) for details

**Integrating New Features?**
- Review [PHASE6_WEBSOCKET.md](./PHASE6_WEBSOCKET.md) for real-time patterns
- Check [MULTI_LANGUAGE_ROADMAP.md](./MULTI_LANGUAGE_ROADMAP.md) for expansion strategy

**Project Handoff?**
- See [HANDOFF.md](./HANDOFF.md) for complete knowledge transfer

---

**Status:** Architecture finalized and tested ✅
