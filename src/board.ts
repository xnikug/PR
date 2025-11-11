/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import assert from 'node:assert';
import fs from 'node:fs';

/**
 * A mutable, thread-safe Memory Scramble game board.
 * 
 * The board consists of cards arranged in a grid. Each card has a label (string).
 * Cards can be face-up or face-down, and may be controlled by players.
 * Players can flip cards following the game rules:
 * - A player can flip a first card (must be face-down and uncontrolled)
 * - After flipping a first card, the player controls it and can flip a second card
 * - If the second card matches the first, both are removed from the board
 * - If they don't match, both are turned face-down
 * - A player can only control up to 1 card at a time (their "first card")
 */
export class Board {

    private readonly width: number;
    private readonly height: number;
    // cards[row][col] = card label or 'none' if removed
    private readonly cards: string[][];
    // faceUp[row][col] = true if face-up, false if face-down
    private readonly faceUp: boolean[][];
    // controlledBy[row][col] = playerId controlling the card, or undefined
    private readonly controlledBy: Map<string, string>; // key: "row,col", value: playerId
    // firstCard[playerId] = "row,col" of the first card they flipped, or undefined
    private readonly firstCard: Map<string, string>; // key: playerId, value: "row,col"
    // lastTurnCards[playerId] = Set of "row,col" positions from player's last turn (non-matching cards)
    private readonly lastTurnCards: Map<string, Set<string>>; // key: playerId, value: Set of positions
    // matchedCards[playerId] = Set of "row,col" positions from player's last successful match
    private readonly matchedCards: Map<string, Set<string>>; // key: playerId, value: Set of matched positions
    // matchCount[playerId] = number of successful matches (pairs) this player has made
    private readonly matchCount: Map<string, number>; // key: playerId, value: match count
    // changeListeners waiting for board changes
    private changeListeners: Array<() => void> = [];
    // waitingQueues[position] = queue of {playerId, resolve} for players waiting for this position
    private readonly waitingQueues: Map<string, Array<{playerId: string, resolve: () => void}>> = new Map();
    // playerColors[playerId] = color assigned to this player
    private readonly playerColors: Map<string, string> = new Map();
    // removedBy[position] = playerId who removed the card at this position
    private readonly removedBy: Map<string, string> = new Map(); // key: "row,col", value: playerId
    
    // Available colors for players
    private static readonly COLORS = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B88B', '#AAB7B8'
    ];
    private colorIndex = 0;

    // Abstraction function:
    //   AF(width, height, cards, faceUp, controlledBy, firstCard, lastTurnCards, matchCount) = 
    //     a Memory Scramble game board of size width x height where:
    //     - cards[r][c] is the label of the card at position (r,c), or 'none' if removed
    //     - faceUp[r][c] indicates whether the card at (r,c) is face-up
    //     - controlledBy maps "r,c" to the playerId controlling that card
    //     - firstCard maps playerId to "r,c" of their first flipped card
    //     - lastTurnCards maps playerId to positions of their last non-matching pair
    //     - matchCount tracks successful matches per player
    //
    // Representation invariant:
    //   - width > 0 and height > 0
    //   - cards.length == height and cards[r].length == width for all r
    //   - faceUp.length == height and faceUp[r].length == width for all r
    //   - if cards[r][c] == 'none', then faceUp[r][c] == false and "r,c" not in controlledBy
    //   - if "r,c" in controlledBy with value playerId, then either:
    //       * firstCard[playerId] == "r,c" (player's current first card), OR
    //       * "r,c" is in matchedCards[playerId] (player's matched card from last turn)
    //   - if firstCard[playerId] == "r,c", then "r,c" in controlledBy with value playerId
    //   - each playerId appears at most once in firstCard (i.e., controls at most 1 first card)
    //   - for all cards, the label is a non-empty string (except 'none')
    //
    // Safety from rep exposure:
    //   - All fields are private and readonly (except changeListeners which is mutated internally)
    //   - width and height are immutable numbers
    //   - cards and faceUp are mutable arrays, never returned directly to clients
    //   - controlledBy, firstCard, lastTurnCards, and matchCount are private Maps, never exposed
    //   - All public methods return strings or Promises of strings
    //   - Thread safety achieved through async/await and internal promise coordination

    /**
     * Create a new Memory Scramble board.
     * 
     * @param width width of the board (number of columns), must be > 0
     * @param height height of the board (number of rows), must be > 0
     * @param cards array of card labels, must have exactly width * height elements,
     *              each element must be a non-empty string
     */
    private constructor(width: number, height: number, cards: string[]) {
        this.width = width;
        this.height = height;
        this.cards = [];
        this.faceUp = [];
        this.controlledBy = new Map();
        this.firstCard = new Map();
        this.lastTurnCards = new Map();
        this.matchedCards = new Map();
        this.matchCount = new Map();

        // Initialize the board grid
        let index = 0;
        for (let r = 0; r < height; r++) {
            this.cards[r] = [];
            this.faceUp[r] = [];
            for (let c = 0; c < width; c++) {
                this.cards[r]![c] = cards[index]!;
                this.faceUp[r]![c] = false;
                index++;
            }
        }

        this.checkRep();
    }

    /**
     * Check the representation invariant.
     * @throws Error if the rep invariant is violated
     */
    private checkRep(): void {
        assert(this.width > 0, 'width must be positive');
        assert(this.height > 0, 'height must be positive');
        assert(this.cards.length === this.height, 'cards length mismatch');
        assert(this.faceUp.length === this.height, 'faceUp length mismatch');

        for (let r = 0; r < this.height; r++) {
            assert(this.cards[r]!.length === this.width, `cards row ${r} width mismatch`);
            assert(this.faceUp[r]!.length === this.width, `faceUp row ${r} width mismatch`);
            
            for (let c = 0; c < this.width; c++) {
                const card = this.cards[r]![c]!;
                assert(card.length > 0, 'card label must be non-empty');
                
                if (card === 'none') {
                    assert(this.faceUp[r]![c] === false, 'removed card must be face-down');
                    assert(!this.controlledBy.has(`${r},${c}`), 'removed card cannot be controlled');
                }
            }
        }

        // Check consistency between controlledBy and firstCard
        for (const [pos, playerId] of this.controlledBy.entries()) {
            const isFirstCard = this.firstCard.get(playerId) === pos;
            const isMatchedCard = this.matchedCards.get(playerId)?.has(pos) ?? false;
            assert(isFirstCard || isMatchedCard, 'controlledBy/firstCard or matchedCards mismatch');
        }
        for (const [playerId, pos] of this.firstCard.entries()) {
            assert(this.controlledBy.get(pos) === playerId, 'firstCard/controlledBy mismatch');
        }
    }

    /**
     * Make a new board by parsing a file.
     * 
     * File format:
     * - First line: WIDTHxHEIGHT (e.g., "5x5")
     * - Following lines: one card label per line, exactly WIDTH * HEIGHT labels
     * 
     * @param filename path to game board file
     * @returns a new board with the size and cards from the file
     * @throws Error if the file cannot be read or is not a valid game board
     */
    public static async parseFromFile(filename: string): Promise<Board> {
        const content = await fs.promises.readFile(filename, 'utf-8');
        const lines = content.split('\n').map(line => line.trim()).filter(line => line.length > 0);
        
        if (lines.length === 0) {
            throw new Error('Empty file');
        }

        // Parse dimensions
        const dimensionMatch = lines[0]!.match(/^(\d+)x(\d+)$/);
        if (!dimensionMatch) {
            throw new Error('First line must be WIDTHxHEIGHT');
        }

        const width = parseInt(dimensionMatch[1]!);
        const height = parseInt(dimensionMatch[2]!);

        if (width <= 0 || height <= 0) {
            throw new Error('Width and height must be positive');
        }

        // Parse cards
        const cards = lines.slice(1);
        if (cards.length !== width * height) {
            throw new Error(`Expected ${width * height} cards, got ${cards.length}`);
        }

        return new Board(width, height, cards);
    }

    /**
     * Get the color assigned to a player, assigning one if they don't have one yet.
     * 
     * @param playerId ID of the player
     * @returns hex color code for the player
     */
    private getPlayerColor(playerId: string): string {
        let color = this.playerColors.get(playerId);
        if (!color) {
            color = Board.COLORS[this.colorIndex % Board.COLORS.length]!;
            this.colorIndex++;
            this.playerColors.set(playerId, color);
        }
        return color;
    }

    /**
     * Get the current state of the board from a player's perspective.
     * 
     * @param playerId ID of the player viewing the board
     * @returns string representation of the board state:
     *          First line: "WIDTHxHEIGHT playerColor\n"
     *          Then WIDTH*HEIGHT lines, each containing:
     *          "down", "none", "none <color>", "up <label>", or "my <label>"
     */
    public async look(playerId: string): Promise<string> {
        this.checkRep();
        
        const playerColor = this.getPlayerColor(playerId);
        let result = `${this.width}x${this.height} ${playerColor}\n`;
        
        for (let r = 0; r < this.height; r++) {
            for (let c = 0; c < this.width; c++) {
                const card = this.cards[r]![c]!;
                const isFaceUp = this.faceUp[r]![c]!;
                const controller = this.controlledBy.get(`${r},${c}`);
                const pos = `${r},${c}`;
                
                if (card === 'none') {
                    // Card has been removed - include who removed it
                    const remover = this.removedBy.get(pos);
                    if (remover) {
                        const removerColor = this.getPlayerColor(remover);
                        result += `none ${removerColor}\n`;
                    } else {
                        result += 'none\n';
                    }
                } else if (controller === playerId) {
                    // Card is controlled by this player
                    result += `my ${card}\n`;
                } else if (isFaceUp) {
                    // Card is face-up and visible to everyone
                    result += `up ${card}\n`;
                } else {
                    // Card is face-down
                    result += 'down\n';
                }
            }
        }
        
        this.checkRep();
        return result;
    }

    /**
     * Attempt to flip a card at the given position.
     * 
     * Rules:
     * - If this is the player's first card: card must be face-down and not controlled
     * - If this is the player's second card: player must control exactly one other card
     * - After flipping second card: if match, both removed; if no match, both face-down
     * 
     * @param playerId ID of the player flipping the card
     * @param row row of the card to flip
     * @param column column of the card to flip
     * @returns the new board state from the player's perspective
     * @throws Error if the flip is invalid
     */
    public async flip(playerId: string, row: number, column: number): Promise<string> {
        this.checkRep();

        // Validate coordinates
        if (row < 0 || row >= this.height || column < 0 || column >= this.width) {
            throw new Error('Invalid coordinates');
        }

        const pos = `${row},${column}`;
        const card = this.cards[row]![column]!;

        // Can't flip a removed card
        if (card === 'none') {
            throw new Error('Card has been removed');
        }

        const firstCardPos = this.firstCard.get(playerId);

        if (firstCardPos === undefined) {
            // This is the first card
            
            // Remove matched cards from this player's last turn
            const playerMatchedCards = this.matchedCards.get(playerId);
            if (playerMatchedCards) {
                for (const cardPos of playerMatchedCards) {
                    const [r, c] = cardPos.split(',').map(Number);
                    if (this.cards[r!]![c!] !== 'none') {
                        this.cards[r!]![c!] = 'none';
                        this.faceUp[r!]![c!] = false;
                        this.controlledBy.delete(cardPos);
                        this.removedBy.set(cardPos, playerId);
                        // Notify anyone waiting for this position
                        this.notifyPositionAvailable(cardPos);
                    }
                }
                this.matchedCards.delete(playerId);
            }
            
            // Turn face-down only THIS player's cards from their last turn (if they didn't match)
            const playerLastTurnCards = this.lastTurnCards.get(playerId);
            if (playerLastTurnCards) {
                for (const cardPos of playerLastTurnCards) {
                    const [r, c] = cardPos.split(',').map(Number);
                    if (this.cards[r!]![c!] !== 'none' && !this.controlledBy.has(cardPos)) {
                        this.faceUp[r!]![c!] = false;
                    }
                }
                this.lastTurnCards.delete(playerId);
            }
            
            // Wait if someone else controls it
            await this.waitUntilNotControlled(pos, playerId);
            
            // Check again after waiting - only check if removed, not if face-up
            if (this.cards[row]![column] === 'none') {
                throw new Error('Card was removed while waiting');
            }

            // Flip it face-up and take control (even if it was already face-up from another player's turn)
            this.faceUp[row]![column] = true;
            this.controlledBy.set(pos, playerId);
            this.firstCard.set(playerId, pos);
            this.notifyChange();

        } else {
            // This is the second card
            if (pos === firstCardPos) {
                // Relinquish control of first card before failing
                this.controlledBy.delete(firstCardPos);
                this.firstCard.delete(playerId);
                this.notifyPositionAvailable(firstCardPos);
                throw new Error('Cannot flip the same card twice');
            }

            // Check if card was removed (rule 2-A)
            if (card === 'none') {
                // Relinquish control of first card before failing
                this.controlledBy.delete(firstCardPos);
                this.firstCard.delete(playerId);
                this.notifyPositionAvailable(firstCardPos);
                throw new Error('Card has been removed');
            }

            // Check if it's already face-up and controlled by another player (rule 2-B)
            // Do NOT wait in this case - fail immediately to avoid deadlock
            const controller = this.controlledBy.get(pos);
            if (this.faceUp[row]![column] && controller !== undefined && controller !== playerId) {
                // Relinquish control of first card before failing
                this.controlledBy.delete(firstCardPos);
                this.firstCard.delete(playerId);
                this.notifyPositionAvailable(firstCardPos);
                throw new Error('Card is already controlled by another player');
            }

            // Only wait if the card is face-down or not controlled
            if (controller !== undefined && controller !== playerId) {
                await this.waitUntilNotControlled(pos, playerId);
            }

            // Check if still valid after waiting
            if (this.cards[row]![column] === 'none') {
                // Relinquish control of first card before failing
                this.controlledBy.delete(firstCardPos);
                this.firstCard.delete(playerId);
                this.notifyPositionAvailable(firstCardPos);
                throw new Error('Card was removed while waiting');
            }
            
            // Flip the second card face-up
            this.faceUp[row]![column] = true;
            this.notifyChange();

            // Check for match
            const [firstRow, firstCol] = firstCardPos.split(',').map(Number);
            const firstCardLabel = this.cards[firstRow!]![firstCol!]!;
            const secondCardLabel = card;

            if (firstCardLabel === secondCardLabel) {
                // Match! Keep both cards face-up and controlled by this player
                // Don't delete from controlledBy - keep the first card controlled
                // Add the second card to controlledBy as well
                this.controlledBy.set(pos, playerId);
                
                const matchedSet = new Set<string>([firstCardPos, pos]);
                this.matchedCards.set(playerId, matchedSet);

                // Increment match count
                const currentMatchCount = this.matchCount.get(playerId) || 0;
                this.matchCount.set(playerId, currentMatchCount + 1);
                
                // Don't release control - player keeps both matched cards
                // Only remove from firstCard so they can flip a new first card next turn
                this.firstCard.delete(playerId);
            } else {
                // No match - keep both face-up and track them for later cleanup
                // They will be turned face-down when THIS player starts their next turn
                const lastTurnSet = new Set<string>([firstCardPos, pos]);
                this.lastTurnCards.set(playerId, lastTurnSet);
                
                // Release control and notify waiting players
                this.controlledBy.delete(firstCardPos);
                this.firstCard.delete(playerId);
                this.notifyPositionAvailable(firstCardPos);
            }
            this.notifyChange();
        }

        this.checkRep();
        return this.look(playerId);
    }

    /**
     * Wait until a position is not controlled by another player.
     * Uses a position-specific queue to ensure FIFO ordering.
     * 
     * @param pos position to check
     * @param playerId ID of the player trying to control the position
     */
    private async waitUntilNotControlled(pos: string, playerId: string): Promise<void> {
        while (true) {
            const controller = this.controlledBy.get(pos);
            if (controller === undefined || controller === playerId) {
                // Position is available
                return;
            }
            
            // Position is controlled by someone else - join the queue
            const { promise, resolve } = Promise.withResolvers<void>();
            
            // Get or create the queue for this position
            let queue = this.waitingQueues.get(pos);
            if (!queue) {
                queue = [];
                this.waitingQueues.set(pos, queue);
            }
            
            // Add this player to the queue
            queue.push({ playerId, resolve });
            
            // Wait until we're notified
            await promise;
            
            // After being notified, check if the position is now available
            // (it might have been removed or still controlled)
        }
    }

    /**
     * Notify the next waiting player for a specific position.
     * 
     * @param pos position that became available
     */
    private notifyPositionAvailable(pos: string): void {
        const queue = this.waitingQueues.get(pos);
        if (queue && queue.length > 0) {
            // Notify the first player in the queue
            const next = queue.shift();
            if (next) {
                next.resolve();
            }
            
            // Clean up empty queue
            if (queue.length === 0) {
                this.waitingQueues.delete(pos);
            }
        }
    }

    /**
     * Wait for the next change to the board.
     * 
     * @returns a promise that resolves when the board changes
     */
    private async waitForChange(): Promise<void> {
        const { promise, resolve } = Promise.withResolvers<void>();
        this.changeListeners.push(resolve);
        return promise;
    }

    /**
     * Notify all listeners that the board has changed.
     */
    private notifyChange(): void {
        const listeners = this.changeListeners;
        this.changeListeners = [];
        for (const listener of listeners) {
            listener();
        }
    }

    /**
     * Apply a mapping function to all cards on the board.
     * 
     * This maintains pairwise consistency: if two cards match before the map,
     * they will continue to match during and after the map operation.
     * 
     * @param playerId ID of the player performing the map
     * @param f mapping function from card labels to new card labels
     * @returns the new board state from the player's perspective
     */
    public async map(playerId: string, f: (card: string) => Promise<string>): Promise<string> {
        this.checkRep();

        // Build a mapping from old labels to new labels
        const labelMap = new Map<string, string>();

        // Collect all unique card labels (except 'none')
        const uniqueLabels = new Set<string>();
        for (let r = 0; r < this.height; r++) {
            for (let c = 0; c < this.width; c++) {
                const card = this.cards[r]![c]!;
                if (card !== 'none') {
                    uniqueLabels.add(card);
                }
            }
        }

        // Apply the function to each unique label
        for (const label of uniqueLabels) {
            const newLabel = await f(label);
            labelMap.set(label, newLabel);
        }

        // Apply the mapping to all cards
        for (let r = 0; r < this.height; r++) {
            for (let c = 0; c < this.width; c++) {
                const card = this.cards[r]![c]!;
                if (card !== 'none') {
                    const newLabel = labelMap.get(card);
                    if (newLabel !== undefined && newLabel !== card) {
                        this.cards[r]![c] = newLabel;
                    }
                }
            }
        }

        this.notifyChange();
        this.checkRep();
        return this.look(playerId);
    }

    /**
     * Watch for changes to the board.
     * 
     * @param playerId ID of the player watching
     * @returns the new board state after a change occurs
     */
    public async watch(playerId: string): Promise<string> {
        this.checkRep();
        await this.waitForChange();
        return this.look(playerId);
    }

    /**
     * Get the leaderboard showing how many matches each player has made.
     * 
     * @returns string with each line containing "playerId: count" sorted by count descending
     */
    public getLeaderboard(): string {
        // Convert matchCount to array and sort by count (descending), then by playerId (ascending)
        const leaderboard = Array.from(this.matchCount.entries())
            .sort((a, b) => {
                const countDiff = b[1] - a[1]; // Sort by count descending
                if (countDiff !== 0) return countDiff;
                return a[0].localeCompare(b[0]); // Then by playerId ascending
            });
        
        if (leaderboard.length === 0) {
            return 'No matches yet';
        }
        
        return leaderboard.map(([playerId, count]) => `${playerId}: ${count}`).join('\n');
    }
}
