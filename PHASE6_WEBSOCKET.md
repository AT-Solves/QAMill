# Phase 6: Real-time Dashboards with WebSocket

**Status:** ✅ COMPLETE - Infrastructure Ready  
**Features:** Live analysis updates, real-time progress, team activity  
**Architecture:** Publisher-Subscriber pattern with connection management  

---

## What's Implemented

### Backend WebSocket Infrastructure

**ConnectionManager** (websocket_manager.py)
```python
- Manages WebSocket connections per user
- Tracks analysis subscribers
- Tracks project subscribers
- Broadcasts updates to multiple users
- Handles disconnections gracefully
- Thread-safe operations
```

**WebSocket Routes** (routes_websocket.py)
```
WS  /ws/analysis/{analysis_id}      # Subscribe to analysis updates
WS  /ws/project/{project_id}        # Subscribe to project updates
POST /ws/broadcast/analysis/:id     # Broadcast analysis update
POST /ws/broadcast/project/:id      # Broadcast project update
GET  /ws/status                     # Get WebSocket status
```

**Message Types**
```json
{
  "type": "connected",
  "analysis_id": "...",
  "connection_id": "..."
}

{
  "type": "analysis_update",
  "event": "mutation_generated",
  "analysis_id": "...",
  "data": { "total": 100, "completed": 45 }
}

{
  "type": "activity",
  "project_id": "...",
  "user_id": "...",
  "activity_type": "analysis_started"
}
```

### Frontend WebSocket Integration

**useWebSocket Composable** (src/composables/useWebSocket.ts)
```typescript
- Connect to WebSocket endpoint with JWT token
- Automatic reconnection
- Message handling
- Connection status tracking
- Error handling
- Graceful disconnection
```

**Usage Example**
```typescript
const { isConnected, messages, send } = useWebSocket(
  '/ws/analysis/abc123'
)

// Listen to messages
const latestMessage = computed(() => {
  return messages.value[messages.value.length - 1]
})
```

---

## Real-time Features

### 1. Live Mutation Analysis

**Event:** `mutation_generated`
```json
{
  "type": "analysis_update",
  "event": "mutation_generated",
  "analysis_id": "abc123",
  "data": {
    "total": 500,
    "completed": 150,
    "killed": 95,
    "survived": 55,
    "percentage": 30
  }
}
```

### 2. Test Execution Progress

**Event:** `test_running`
```json
{
  "type": "analysis_update",
  "event": "test_running",
  "analysis_id": "abc123",
  "data": {
    "mutation_id": "mut_001",
    "file": "calculator.py",
    "line": 45
  }
}
```

### 3. Analysis Completion

**Event:** `analysis_complete`
```json
{
  "type": "analysis_update",
  "event": "analysis_complete",
  "analysis_id": "abc123",
  "data": {
    "mutation_score": 87.5,
    "coverage_score": 92.3,
    "quality_score": 89.9,
    "duration_seconds": 235
  }
}
```

### 4. Team Activity Feed

**Event:** `user_joined_analysis`
```json
{
  "type": "activity",
  "project_id": "proj_001",
  "user_id": "user_001",
  "activity_type": "user_joined_analysis",
  "details": {
    "analysis_id": "abc123",
    "user_name": "Alice"
  }
}
```

---

## Architecture

### Publisher-Subscriber Pattern

```
Analysis Service
    ↓
broadcast_analysis_update()
    ↓
ConnectionManager
    ↓
All subscribed users
```

### Connection Lifecycle

1. **Connect**
   - User opens WebSocket
   - JWT token validated
   - Connection registered

2. **Subscribe**
   - User subscribes to analysis
   - Added to subscriber set
   - Receives broadcasts

3. **Broadcast**
   - Analysis service publishes update
   - Sent to all subscribers
   - Delivered in real-time

4. **Disconnect**
   - User closes WebSocket
   - Automatically unsubscribed
   - Connection cleaned up

---

## Security

✅ **JWT Authentication**
- Token required for WebSocket connection
- Validated before accepting

✅ **User Isolation**
- Users only receive updates they subscribed to
- No cross-user data leakage

✅ **Connection Management**
- Automatic cleanup on disconnect
- No dangling connections

✅ **Rate Limiting Ready**
- Can add message rate limiting
- Can throttle broadcasts

---

## Performance

### Connection Efficiency

- Single connection per analysis
- Single connection per project
- Minimal memory overhead
- Automatic cleanup

### Broadcast Performance

- O(n) where n = subscribers
- Async sends (non-blocking)
- Error handling per subscriber
- Failed sends don't affect others

### Scalability

- Horizontal scaling ready
- Works with load balancers
- Can use Redis pub/sub for multi-server

---

## Integration Points

### Analysis Service

When analysis completes, call:
```python
await manager.broadcast_analysis_update(
    analysis_id="abc123",
    event_type="analysis_complete",
    data={
        "mutation_score": 87.5,
        "coverage_score": 92.3,
        "duration_seconds": 235
    }
)
```

### Team Collaboration

Broadcast team activity:
```python
await manager.broadcast_activity(
    project_id="proj_001",
    user_id="user_001",
    activity_type="analysis_started",
    details={"analysis_id": "abc123"}
)
```

---

## Next Steps

### 1. Update Analysis Service

Modify `analysis_service.py` to broadcast progress:
- After mutation generation
- After each test completes
- On analysis completion
- On error

### 2. Create Dashboard Components

Build real-time UI components:
- Live progress bar
- Real-time mutation score
- Team activity feed
- Live notifications

### 3. Add Notification System

Send notifications for:
- Analysis started
- Analysis completed
- Test gaps found
- Team member activities

---

## Testing WebSocket

### Manual Testing

```bash
# Terminal 1: Start backend
python main_new.py

# Terminal 2: WebSocket CLI tool
wscat -c "ws://localhost:8765/ws/analysis/test123?token=YOUR_JWT_TOKEN"

# Terminal 3: Broadcast update
curl -X POST "http://localhost:8765/ws/broadcast/analysis/test123?event_type=mutation_generated" \
  -H "Content-Type: application/json"
```

### Browser Testing

```javascript
// In browser console
const ws = new WebSocket(
  'ws://localhost:8765/ws/analysis/test123?token=' + auth_token
)

ws.onmessage = (e) => {
  console.log('Message:', JSON.parse(e.data))
}

// Send message
ws.send(JSON.stringify({ type: 'ping' }))
```

---

## Roadmap

### Immediate (Phase 6)

- ✅ WebSocket infrastructure
- ✅ Connection management
- ⏳ Dashboard real-time updates
- ⏳ Team activity feed
- ⏳ Live notifications

### Next (Phase 7)

- Integration with analysis service
- Dashboard components
- Notification system
- Production deployment

---

## Key Files

**Backend:**
- `websocket_manager.py` - Connection management
- `routes_websocket.py` - WebSocket routes
- `main_new.py` - Registered router

**Frontend:**
- `composables/useWebSocket.ts` - WebSocket hook
- Future: Dashboard components

---

## Summary

**Phase 6 provides the infrastructure for real-time QAMill:**
- Live mutation analysis progress
- Real-time test results
- Team activity feeds
- Instant notifications

**Next: Update UI components to consume real-time data**

Ready for Phase 7: Production Deployment! 🚀
