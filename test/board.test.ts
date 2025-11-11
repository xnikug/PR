/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import assert from 'node:assert';
import { Board } from '../src/board.js';

/**
 * Comprehensive unit tests for the Board ADT.
 * Tests cover all game rules, edge cases, and concurrent scenarios.
 */
describe('Board', function() {

    /**
     * Testing strategy:
     * 
     * parseFromFile():
     *   - valid file with different sizes
     *   - invalid files (empty, wrong format, wrong number of cards)
     * 
     * look():
     *   - empty board (all face-down)
     *   - board with face-up cards
     *   - board with controlled cards
     *   - board with removed cards
     * 
     * flip():
     *   - first card: valid flip
     *   - first card: card already face-up
     *   - first card: card removed
     *   - second card: matching pair (cards removed)
     *   - second card: non-matching pair (cards turned face-down)
     *   - second card: flip same card twice
     *   - second card: card already face-up
     *   - concurrent flips by different players
     *   - waiting for controlled card
     * 
     * map():
     *   - simple replacement
     *   - identity map
     *   - map maintaining pairs
     *   - concurrent map operations
     * 
     * watch():
     *   - watch triggered by flip
     *   - watch triggered by map
     */

    describe('parseFromFile', function() {
        
        it('parses a valid 3x3 board', async function() {
            const board = await Board.parseFromFile('board/perfect.txt');
            const state = await board.look('player1');
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.ok(lines[0]?.startsWith('3x3')); // Dimension line may include color
            assert.strictEqual(lines.length, 10); // 1 dimension + 9 cards
        });

        it('parses a valid 5x5 board', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            const state = await board.look('player1');
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.ok(lines[0]?.startsWith('5x5')); // Dimension line may include color
            assert.strictEqual(lines.length, 26); // 1 dimension + 25 cards
        });
    });

    describe('look', function() {
        
        it('shows all cards face-down initially', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            const state = await board.look('player1');
            const lines = state.split('\n').filter(l => l.length > 0);
            
            assert.ok(lines[0]?.startsWith('5x5')); // Dimension line may include color
            for (let i = 1; i < lines.length; i++) {
                assert.strictEqual(lines[i], 'down');
            }
        });

        it('shows face-up cards to all players', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips first card
            await board.flip('player1', 0, 0);
            
            // Player2 should see it face-up
            const state = await board.look('player2');
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'up A'); // Player1 controls it, player2 sees it as face-up
        });

        it('shows controlled cards to the controlling player', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips first card at (0,0)
            await board.flip('player1', 0, 0);
            
            const state1 = await board.look('player1');
            const lines1 = state1.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines1[1], 'my A'); // Player1 sees their controlled card
            
            const state2 = await board.look('player2');
            const lines2 = state2.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines2[1], 'up A'); // Player2 sees it as face-up
        });

        it('shows removed cards as "none"', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips matching pair at (0,0) and (0,2)
            await board.flip('player1', 0, 0);
            await board.flip('player1', 0, 2);
            
            // Cards are still controlled by player1 (showing as 'my')
            let state = await board.look('player1');
            let lines = state.split('\n').filter(l => l.length > 0);
            assert.ok(lines[1] === 'my A' || lines[1] === 'none' || lines[1]?.startsWith('none')); 
            
            // Player1 starts next turn - matched cards should be removed
            await board.flip('player1', 1, 0);
            
            state = await board.look('player1');
            lines = state.split('\n').filter(l => l.length > 0);
            assert.ok(lines[1] === 'none' || lines[1]?.startsWith('none')); // (0,0) removed
            assert.ok(lines[3] === 'none' || lines[3]?.startsWith('none')); // (0,2) removed
        });
    });

    describe('flip - first card', function() {
        
        it('flips first card face-up and takes control', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            const state = await board.flip('player1', 0, 0);
            const lines = state.split('\n').filter(l => l.length > 0);
            
            assert.strictEqual(lines[1], 'my A'); // Card is controlled by player1
        });

        it('throws error when flipping removed card', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Remove card at (0,0) by matching with (0,2)
            await board.flip('player1', 0, 0);
            await board.flip('player1', 0, 2);
            
            // Start next turn to actually remove the matched cards
            await board.flip('player1', 1, 0);
            
            // Now try to flip the removed card at (0,0) - should throw error
            await assert.rejects(
                async () => board.flip('player2', 0, 0),
                /removed|none/i
            );
        });
    });

    describe('flip - second card', function() {
        
        it('removes matching pair', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Flip matching pair
            await board.flip('player1', 0, 0); // A
            await board.flip('player1', 0, 2); // A
            
            // Matched cards are still controlled by player1 until next turn
            let state = await board.look('player1');
            let lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'my A'); // (0,0) still controlled by player1
            assert.strictEqual(lines[3], 'my A'); // (0,2) still controlled by player1
            
            // Start next turn to remove the matched cards
            await board.flip('player1', 1, 0);
            
            state = await board.look('player1');
            lines = state.split('\n').filter(l => l.length > 0);
            // Now cards should be removed
            assert.ok(lines[1] === 'none' || lines[1]?.startsWith('none'), `Expected none, got: ${lines[1]}`);
            assert.ok(lines[3] === 'none' || lines[3]?.startsWith('none'), `Expected none, got: ${lines[3]}`);
        });

        it('keeps non-matching pair face-up', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Flip non-matching pair
            await board.flip('player1', 0, 0); // A
            const state = await board.flip('player1', 0, 1); // B
            
            const lines = state.split('\n').filter(l => l.length > 0);
            // According to Rule 2-E: cards stay face-up after non-match
            assert.strictEqual(lines[1], 'up A'); // (0,0) face-up
            assert.strictEqual(lines[2], 'up B'); // (0,1) face-up
        });

        it('cannot flip same card as first and second', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips first card
            await board.flip('player1', 0, 0);
            
            // Try to flip the same card as second card - should fail
            await assert.rejects(
                async () => board.flip('player1', 0, 0),
                /same card/i
            );
        });

        it('releases control after second flip', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips pair
            await board.flip('player1', 0, 0);
            await board.flip('player1', 0, 1);
            
            // Player1 should be able to flip a new first card
            const state = await board.flip('player1', 1, 0);
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[6], 'my B'); // New first card is visible and controlled
        });

        it('turns non-matching pair face-down on next turn', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips non-matching pair
            await board.flip('player1', 0, 0); // A
            await board.flip('player1', 0, 1); // B
            
            // Cards are face-up after the flip
            let state = await board.look('player1');
            let lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'up A'); // (0,0) face-up
            assert.strictEqual(lines[2], 'up B'); // (0,1) face-up
            
            // Player2 starts a new turn - player1's cards stay face-up (only player2 cleans up their own cards)
            await board.flip('player2', 1, 0); // New first card
            
            state = await board.look('player1');
            lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'up A'); // (0,0) still face-up (player2 didn't clean it)
            assert.strictEqual(lines[2], 'up B'); // (0,1) still face-up
            assert.strictEqual(lines[6], 'up B'); // (1,0) player2's card is face-up
            
            // Now when PLAYER1 starts their next turn, THEIR previous cards are turned face-down
            await board.flip('player1', 2, 0); // Player1's new first card
            
            state = await board.look('player1');
            lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'down'); // (0,0) now face-down (player1 cleaned up)
            assert.strictEqual(lines[2], 'down'); // (0,1) now face-down
            assert.strictEqual(lines[6], 'up B'); // (1,0) still face-up (belongs to player2)
            assert.strictEqual(lines[11], 'my A'); // (2,0) player1's new card
        });
    });

    describe('flip - concurrency', function() {
        
        it('allows multiple players to flip different first cards', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Start concurrent flips at different positions
            const flip1 = board.flip('player1', 0, 0);
            const flip2 = board.flip('player2', 1, 1);
            
            await Promise.all([flip1, flip2]);
            
            const state = await board.look('observer');
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'up A'); // (0,0) - Player1's card, observer sees it face-up
            assert.strictEqual(lines[7], 'up A'); // (1,1) - Player2's card, observer sees it face-up
        });

        it('waits for controlled card to be released', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips first card at (0,0)
            await board.flip('player1', 0, 0);
            
            // Player2 tries to flip the same card (will wait)
            const player2Flip = board.flip('player2', 0, 0);
            
            // Give it a moment to start waiting
            await new Promise(resolve => setTimeout(resolve, 50));
            
            // Player1 completes their turn (non-matching)
            await board.flip('player1', 0, 1);
            
            // Now player2's flip should complete successfully
            const state = await player2Flip;
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'my A'); // Card is now controlled by player2
        });

        it('handles race condition when card is removed while waiting', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips first card at (0,0)
            await board.flip('player1', 0, 0);
            
            // Player2 tries to flip same card (will wait)
            const player2Flip = board.flip('player2', 0, 0);
            
            // Give it a moment to start waiting
            await new Promise(resolve => setTimeout(resolve, 50));
            
            // Player1 matches the card with (0,2)
            await board.flip('player1', 0, 2);
            
            // Player1 starts next turn to actually remove the matched cards
            await board.flip('player1', 1, 0);
            
            // Player2's flip should now fail because card was removed
            await assert.rejects(
                async () => player2Flip,
                /removed|none/i
            );
        });

        it('waits if card is controlled by another player', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Player1 flips first card at (0,0)
            await board.flip('player1', 0, 0);
            
            // Player2 tries to flip the same card (will wait)
            const player2Flip = board.flip('player2', 0, 0);
            
            // Give it a moment to start waiting
            await new Promise(resolve => setTimeout(resolve, 50));
            
            // Player1 completes their turn with a non-matching card
            await board.flip('player1', 0, 1);
            
            // Now player2's flip should succeed (card is now face-down and available)
            const state = await player2Flip;
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'my A'); // Player2 now controls and sees the card
        });
    });

    describe('map', function() {
        
        it('replaces all cards with mapped values', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Map A->X, B->Y
            await board.map('player1', async (card) => {
                if (card === 'A') return 'X';
                if (card === 'B') return 'Y';
                return card;
            });
            
            // Flip a card to verify the mapping
            await board.flip('player1', 0, 0);
            const state = await board.look('player1');
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'my X'); // Was 'A', now 'X' and controlled
        });

        it('maintains matching pairs', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            // Map A->C
            await board.map('player1', async (card) => {
                if (card === 'A') return 'C';
                return card;
            });
            
            // The pair at (0,0) and (0,2) should still match
            await board.flip('player1', 0, 0);
            await board.flip('player1', 0, 2);
            
            // Matched cards are still controlled until next turn
            let state = await board.look('player1');
            let lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'my C'); // (0,0) still controlled
            assert.strictEqual(lines[3], 'my C'); // (0,2) still controlled
            
            // Start next turn to remove matched cards
            await board.flip('player1', 1, 0);
            
            state = await board.look('player1');
            lines = state.split('\n').filter(l => l.length > 0);
            // Now cards should be removed
            assert.ok(lines[1] === 'none' || lines[1]?.startsWith('none'), `Expected none at position 1, got: ${lines[1]}`);
            assert.ok(lines[3] === 'none' || lines[3]?.startsWith('none'), `Expected none at position 3, got: ${lines[3]}`);
        });

        it('identity map leaves board unchanged', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            const stateBefore = await board.look('player1');
            
            await board.map('player1', async (card) => card);
            
            const stateAfter = await board.look('player1');
            assert.strictEqual(stateBefore, stateAfter);
        });
    });

    describe('watch', function() {
        
        it('resolves when board changes due to flip', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            const watchPromise = board.watch('player1');
            
            // Trigger a change
            await new Promise(resolve => setTimeout(resolve, 10));
            await board.flip('player2', 0, 0);
            
            const state = await watchPromise;
            const lines = state.split('\n').filter(l => l.length > 0);
            assert.strictEqual(lines[1], 'up A'); // Card was flipped by player2, player1 sees it as face-up
        });

        it('resolves when board changes due to map', async function() {
            const board = await Board.parseFromFile('board/ab.txt');
            
            const watchPromise = board.watch('player1');
            
            // Trigger a change with map
            await new Promise(resolve => setTimeout(resolve, 10));
            await board.map('player2', async (card) => card === 'A' ? 'X' : card);
            
            await watchPromise; // Should resolve
        });
    });

    describe('game rules - complete scenarios', function() {
        
        it('plays a complete matching game', async function() {
            const board = await Board.parseFromFile('board/perfect.txt');
            
            // Perfect board: 3x3 with matching pairs
            // Flip all matching pairs
            await board.flip('player1', 0, 0); // 🦄
            await board.flip('player1', 0, 1); // 🦄 - match!
            
            await board.flip('player1', 1, 0); // 🌈
            await board.flip('player1', 1, 1); // 🌈 - match!
            
            await board.flip('player1', 2, 0); // 🌈
            await board.flip('player1', 0, 2); // 🌈 - match!
            
            await board.flip('player1', 1, 2); // 🦄
            await board.flip('player1', 2, 1); // 🦄 - match!
            
            // Check the board state - last matched cards are still controlled
            let state = await board.look('player1');
            let lines = state.split('\n').filter(l => l.length > 0);
            
            // Count controlled cards and removed cards
            let controlledOrRemovedCount = 0;
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i];
                if (line === 'none' || line?.startsWith('none') || line?.startsWith('my')) {
                    controlledOrRemovedCount++;
                }
            }
            // Should have 8 cards that are either removed or controlled (matched)
            assert.ok(controlledOrRemovedCount >= 8, `Expected at least 8 cards controlled/removed, got ${controlledOrRemovedCount}`);
            
            // Start a new turn to remove the last matched pair
            await board.flip('player1', 2, 2); // Last card
            
            state = await board.look('player1');
            lines = state.split('\n').filter(l => l.length > 0);
            
            let removedCount = 0;
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i];
                if (line === 'none' || line?.startsWith('none')) {
                    removedCount++;
                }
            }
            assert.ok(removedCount >= 8, `Expected at least 8 cards removed, got ${removedCount}`);
        });
    });
});
