# Memory Scramble Game

Complete implementation of a concurrent Memory Scramble card matching game with full game rules, thread safety, and comprehensive testing.

## Table of Contents
- [Running with Docker](#running-with-docker)
- [Running without Docker](#running-without-docker)
- [Running Tests](#running-tests)
- [Running Simulation](#running-simulation)
- [Project Architecture](#project-architecture)
- [Game Rules](#game-rules)
- [Documentation](#documentation)

## Running with Docker

### Quick Start

Build and start the server using Docker Compose:
```bash
docker-compose up
```

The game will be available at http://localhost:8080

### Docker Configuration

The `docker-compose.yml` file configures:
- Port mapping: 8080 (host) → 8080 (container)
- Volume mount: `./board:/app/board:ro` (read-only access to board files)
- Default board: `board/ab.txt` (5×5 grid with A/B cards)
- Automatic rebuild on source changes

### Using Different Board Files

To use a different board file, modify the command in `docker-compose.yml`:
```yaml
command: node dist/src/server.js 8080 board/zoom.txt
```

Or run a standalone container:
```bash
docker-compose down
docker build -t memory-scramble .
docker run -p 8080:8080 -v $(pwd)/board:/app/board:ro memory-scramble node dist/src/server.js 8080 board/zoom.txt
```

### Available Board Files

- **`board/ab.txt`** - 5×5 grid with alternating A and B cards (default)
- **`board/perfect.txt`** - 3×3 grid with emoji pairs (🦄 and 🌈)
- **`board/zoom.txt`** - 5×5 grid with zoom-themed cards
- **`board/test.txt`** - Custom test configuration

### Docker Image Details

The `Dockerfile` creates a multi-stage build:
1. **Build stage**: Installs dependencies and compiles TypeScript
2. **Runtime stage**: Slim Node.js image with only production dependencies
3. **Working directory**: `/app`
4. **Entry point**: Node.js running the compiled server

To rebuild after code changes:
```bash
docker-compose up --build
```

## Running without Docker

### Installation

Install dependencies:
```bash
npm install
```

### Start the Server

```bash
npm start 8080 board/ab.txt
```

The server accepts two arguments:
1. **Port number** (e.g., `8080`)
2. **Board file path** (e.g., `board/ab.txt`)

Access the game at http://localhost:8080

## Running Tests

### Run All Tests

Execute the complete test suite:
```bash
npm test
```

This runs:
1. TypeScript compilation (`tsc`)
2. ESLint code quality checks
3. Mocha test runner with all 23 unit tests

### Test Suite Coverage

The test suite in `test/board.test.ts` validates:

**parseFromFile()**
- ✓ Valid 3×3 board parsing
- ✓ Valid 5×5 board parsing
- File format validation (dimensions, card count)

**look()**
- ✓ All cards face-down initially
- ✓ Face-up cards visible to all players
- ✓ Controlled cards shown to controlling player
- ✓ Removed cards displayed as "none"

**flip() - First Card**
- ✓ Flips card face-up and takes control
- ✓ Error when flipping removed card

**flip() - Second Card**
- ✓ Removes matching pair
- ✓ Keeps non-matching pair face-up
- ✓ Cannot flip same card twice
- ✓ Releases control after second flip
- ✓ Turns non-matching pair face-down on next turn

**flip() - Concurrency**
- ✓ Multiple players flip different cards simultaneously
- ✓ Waits for controlled card to be released
- ✓ Handles race condition when card removed while waiting
- ✓ Waits if card controlled by another player

**map()**
- ✓ Replaces all cards with mapped values
- ✓ Maintains matching pairs after transformation
- ✓ Identity map leaves board unchanged

**watch()**
- ✓ Resolves when board changes due to flip
- ✓ Resolves when board changes due to map

**Complete Game Scenarios**
- ✓ Plays a complete matching game from start to finish

### Code Coverage

Generate a detailed coverage report:
```bash
npm run coverage
```

View the HTML coverage report:
```bash
open coverage/index.html  # macOS
xdg-open coverage/index.html  # Linux
start coverage/index.html  # Windows
```

The coverage report shows line-by-line test coverage for all source files.

### Test Output

All tests include descriptive messages showing:
- Test category (e.g., "Board > flip - concurrency")
- Test name (e.g., "waits for controlled card to be released")
- Execution time for async tests
- Clear assertion errors with expected vs. actual values

## Running Simulation

### Stress Test

Run a concurrent stress test with 4 players:
```bash
npm run simulation
```

### Simulation Configuration

The simulation (`src/simulation.ts`) creates a realistic concurrent game scenario:

- **Players**: 4 concurrent players (player0, player1, player2, player3)
- **Moves per player**: 100 attempted flips
- **Board**: `board/zoom.txt` (5×5 grid)
- **Delays**: Random timeouts between 0.1ms and 2ms between moves
- **No shuffling**: Board remains static during simulation

### What the Simulation Tests

The simulation verifies:
1. **Thread safety**: No crashes or deadlocks under concurrent load
2. **Game rules enforcement**: All flip operations follow rules correctly
3. **Error handling**: Invalid moves are caught and reported
4. **Visual feedback**: Card flips are displayed in real-time

### Simulation Output

The simulation displays:
- Player initialization messages
- Each card flip with coordinates and revealed card
- Match detection (successful and failed)
- Move failures with error messages
- Final statistics:
  - Total moves attempted
  - Successful matches
  - Failed moves

Example output:
```
Starting simulation with 4 players, 100 moves each
Board: board/zoom.txt (5×5)
Delays: 0.1ms - 2ms
════════════════════════════════════════════════════════════

player0 starting...
player1 starting...
player2 starting...
player3 starting...
player0: Flipping card at (0,0)...
player0: Card 1 revealed: 🎯 at (0,0)
player1: Flipping card at (2,3)...
player1: Card 1 revealed: 🎨 at (2,3)
...
Simulation Complete
Total moves attempted: 400
Successful matches: 45
Failed moves: 38
```

### Simulation Use Cases

Run the simulation to:
- **Stress test** the concurrent implementation
- **Verify thread safety** with multiple players
- **Debug race conditions** in concurrent scenarios
- **Demonstrate game behavior** under realistic load

## Project Architecture

The codebase follows a strict three-layer architecture:

### Layer 1: Board ADT (`src/board.ts`)

Core game logic with all state mutations. Includes:
- Representation invariant checks using `assert`
- Abstraction function documentation
- Safety from rep exposure arguments
- Thread safety via async/await coordination
- Position-specific waiting queues for FIFO fairness

Key features:
- **Thread-safe**: Uses promises and waiting queues to coordinate concurrent access
- **Immutable API**: All public methods return new strings, never expose internal state
- **Pairwise consistency**: The `map()` operation maintains matching pairs
- **Player colors**: Automatically assigns unique colors to each player

### Layer 2: Commands Module (`src/commands.ts`)

Thin wrapper layer that:
- Exposes Board methods as simple command functions
- Parses HTTP request parameters
- Formats Board responses for HTTP responses
- Acts as glue code between HTTP and game logic

### Layer 3: HTTP Server (`src/server.ts`)

Routes incoming HTTP requests to command functions:
- `GET /look/{playerId}` - View board state
- `PUT /flip/{playerId}/{row}/{column}` - Flip a card
- `PUT /map/{playerId}` - Apply transformation (with shuffle endpoint)
- `GET /watch/{playerId}` - Wait for board changes

Provided unchanged from course staff.

## Game Rules

### Card Flipping Rules

**First Card**:
- Must be face-down and not controlled by any player
- Becomes face-up and controlled by the player
- If multiple players try to flip the same card, one succeeds and others wait

**Second Card**:
- Player must already control exactly one card (their first card)
- Cannot flip the same card twice
- After flipping:
  - **Match**: Both cards stay controlled until player's next turn, then removed
  - **No match**: Both cards stay face-up until player's next turn, then face-down

### Card States

- **Face-down**: Not visible, shown as "down"
- **Face-up**: Visible to all players, shown as "up {label}"
- **Controlled**: Owned by a player, shown as "my {label}" to owner, "up {label}" to others
- **Removed**: Matched and removed, shown as "none" or "none {color}"

### Concurrency Rules

- Multiple players can flip different first cards simultaneously
- If a player tries to flip a controlled card, they wait in a FIFO queue
- If a card is removed while a player is waiting, their flip fails
- Each player can only control one "first card" at a time

### Map Operation

The `map()` function transforms all card labels while maintaining pairs:
- If two cards matched before the map, they still match after
- Applies the transformation function once per unique label
- All instances of a label are changed to the same new label




Every method in the Board ADT includes:
- Function signature with TypeScript types
- `@param` descriptions for all parameters
- `@returns` documentation for return values
- `@throws` clauses for error conditions
- Preconditions and postconditions
The Board class includes:

**Abstraction Function (AF)**:
Explains how the internal representation maps to the abstract game state of a Memory Scramble board.

**Representation Invariant (RI)**:
Documents all constraints that must hold:
- Dimensions are positive
- Card arrays match dimensions
- Removed cards are face-down and not controlled
- Controlled cards are either first cards or matched cards
- Each player controls at most one first card

**Safety from Rep Exposure**:
Explains why clients cannot corrupt internal state:
- All fields are private and readonly
- Mutable arrays never returned directly
- All public methods return strings or Promises
- Thread safety via async/await coordination

**Thread Safety**:
Uses promise-based coordination:
- Position-specific waiting queues ensure FIFO ordering
- `notifyPositionAvailable()` wakes waiting players
- `waitForChange()` enables watch notifications
- No busy-waiting or polling

## Implementation Details

### Key Features

1. **Deferred removal**: Matched cards stay controlled until player's next turn
2. **Per-player cleanup**: Each player only cleans up their own cards
3. **FIFO waiting**: Players wait in order for controlled cards
4. **Player colors**: Each player gets a unique color (10 colors available)
5. **Match tracking**: Leaderboard shows successful matches per player

### Error Handling

The implementation throws descriptive errors for:
- Invalid coordinates
- Flipping removed cards
- Flipping same card twice
- Cards controlled by other players
- Cards removed while waiting
- Invalid board file format

### Data Structures

- `cards[][]`: 2D array of card labels
- `faceUp[][]`: 2D array of face-up states
- `controlledBy`: Map from position to controlling player
- `firstCard`: Map from player to their first card position
- `lastTurnCards`: Map from player to their non-matching cards
- `matchedCards`: Map from player to their matched cards (pending removal)
- `waitingQueues`: Map from position to queue of waiting players
- `playerColors`: Map from player to assigned color
- `removedBy`: Map from position to player who removed the card