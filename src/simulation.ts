/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import assert from 'node:assert';
import { Board } from './board.js';

/**
 * Simulation script for Memory Scramble game.
 * 
 * Simulates 4 players making random moves with random timeouts between 0.1ms and 2ms.
 * Each player makes 100 moves. No shuffling occurs.
 * 
 * The goal is to verify that the game never crashes under concurrent load.
 * Shows visual feedback of card flips.
 * 
 * @throws Error if an error occurs reading or parsing the board
 */
async function simulationMain(): Promise<void> {
    const filename = 'board/ab.txt';
    const board: Board = await Board.parseFromFile(filename);
    const size = 5;
    const players = 4;
    const tries = 100;
    const minDelayMilliseconds = 0.1;
    const maxDelayMilliseconds = 2;

    console.log(`Starting simulation with ${players} players, ${tries} moves each`);
    console.log(`Board: ${filename} (${size}x${size})`);
    console.log(`Delays: ${minDelayMilliseconds}ms - ${maxDelayMilliseconds}ms`);
    console.log('═'.repeat(60));
    console.log('');

    let totalMoves = 0;
    let successfulMatches = 0;
    let failedMoves = 0;

    // start up one or more players as concurrent asynchronous function calls
    const playerPromises: Array<Promise<void>> = [];
    for (let ii = 0; ii < players; ++ii) {
        playerPromises.push(player(ii));
    }
    // wait for all the players to finish (unless one throws an exception)
    await Promise.all(playerPromises);

    console.log('Simulation Complete');
    console.log(`Total moves attempted: ${totalMoves}`);
    console.log(`Successful matches: ${successfulMatches}`);
    console.log(`Failed moves: ${failedMoves}`);

    /** 
     * Simulate a player making random moves
     * @param playerNumber player to simulate 
     */
    async function player(playerNumber: number): Promise<void> {
        const playerId = `player${playerNumber}`;
        console.log(`${playerId} starting...`);

        for (let jj = 0; jj < tries; ++jj) {
            try {
                await timeout(randomDelay());

                // Look at current board state
                const viewBefore = await board.look(playerId);
                const parsedBefore = parseBoard(viewBefore, size, size);

                // Pick a FIRST card: must be face-down
                const firstPick = pickFaceDown(parsedBefore);
                if (!firstPick) {
                    // No face-down cards left
                    break;
                }
                const { row: row1, col: col1 } = firstPick;
                
                // Show first flip attempt
                console.log(`${playerId}: Flipping card at (${row1},${col1})...`);
                await board.flip(playerId, row1, col1);
                totalMoves++;

                await timeout(randomDelay());

                // Look at board after first flip
                const viewMid = await board.look(playerId);
                const parsedMid = parseBoard(viewMid, size, size);
                
                const card1 = parsedMid[row1]?.[col1];
                if (card1) {
                    console.log(`${playerId}:Card 1 revealed: ${card1.text} at (${row1},${col1})`);
                }

                // Pick a SECOND card: different from first, prefer face-down
                const secondPick = pickSecond(parsedMid, row1, col1);
                if (!secondPick) {
                    // Cannot find valid second card
                    console.log(`${playerId}:No valid second card available`);
                    continue;
                }

                const { row: row2, col: col2 } = secondPick;
                console.log(`${playerId}: Flipping card at (${row2},${col2})...`);
                await board.flip(playerId, row2, col2);
                totalMoves++;

                // Check for match by looking at final board state
                const viewAfter = await board.look(playerId);
                const parsedAfter = parseBoard(viewAfter, size, size);
                
                const cell1 = parsedAfter[row1]?.[col1];
                const cell2 = parsedAfter[row2]?.[col2];

                if (cell2) {
                    console.log(`${playerId}:Card 2 revealed: ${cell2.text} at (${row2},${col2})`);
                }

                // Match if both cards are controlled by this player with same label
                if (cell1 && cell2 && cell1.status === 'my' && cell2.status === 'my' && cell1.text === cell2.text) {
                    successfulMatches++;
                    console.log(`${playerId}:Match! ${cell1.text} = ${cell2.text} (cards at (${row1},${col1}) & (${row2},${col2}))`);
                } else if (cell1 && cell2) {
                    console.log(`${playerId}:No match: ${cell1.text} ≠ ${cell2.text}`);
                }
                console.log(''); // blank line between turns

            } catch (err) {
                // Expected errors: card removed, card controlled, same card twice, etc.
                failedMoves++;
                const errorMsg = err instanceof Error ? err.message : String(err);
                console.log(`${playerId}:Move failed: ${errorMsg}`);
                console.log('');
            }
        }
        
        console.log(`${playerId} completed ${tries} attempts`);
    }

    /**
     * Parse board text into 2D array of {status, text}
     * @param state board state string
     * @param width board width
     * @param height board height
     * @returns 2D array of card info
     */
    function parseBoard(state: string, width: number, height: number): Array<Array<{status: string; text: string}>> {
        const lines = state.split(/\r?\n/).filter(l => l.length > 0);
        // Skip header line
        lines.shift();
        const grid: Array<Array<{status: string; text: string}>> = [];
        let idx = 0;
        for (let r = 0; r < height; r++) {
            const row: Array<{status: string; text: string}> = [];
            for (let c = 0; c < width; c++) {
                const line = lines[idx];
                if (!line) break;
                const parts = line.split(' ');
                const status = parts[0] ?? 'down';
                const text = parts.length > 1 ? parts[1] ?? '' : '';
                row.push({ status, text });
                idx++;
            }
            grid.push(row);
        }
        return grid;
    }

    /**
     * Pick a random face-down card
     * @param grid board grid
     * @returns position or undefined
     */
    function pickFaceDown(grid: Array<Array<{status: string}>>): {row: number; col: number} | undefined {
        const candidates: Array<{row: number; col: number}> = [];
        for (let r = 0; r < grid.length; r++) {
            const rowData = grid[r];
            if (!rowData) continue;
            for (let c = 0; c < rowData.length; c++) {
                const cell = rowData[c];
                if (cell) {
                    candidates.push({ row: r, col: c });
                }
            }
        }
        if (candidates.length === 0) return undefined;
        return candidates[randomInt(candidates.length)];
    }

    /**
     * Pick a second card (different from first)
     * @param grid board grid
     * @param firstRow first card row
     * @param firstCol first card column
     * @returns position or undefined
     */
    function pickSecond(grid: Array<Array<{status: string}>>, firstRow: number, firstCol: number): {row: number; col: number} | undefined {
        const faceDown: Array<{row: number; col: number}> = [];
        const visible: Array<{row: number; col: number}> = [];
        
        for (let r = 0; r < grid.length; r++) {
            const rowData = grid[r];
            if (!rowData) continue;
            for (let c = 0; c < rowData.length; c++) {
                if (r === firstRow && c === firstCol) continue; // Skip first card
                
                const cell = rowData[c];
                if (!cell) continue;
                const st = cell.status;
                if (st === 'down') {
                    faceDown.push({ row: r, col: c });
                } else if (st === 'up') {
                    // Can try face-up cards not controlled by other players
                    visible.push({ row: r, col: c });
                }
            }
        }
        
        // Prefer face-down cards
        if (faceDown.length > 0) {
            return faceDown[randomInt(faceDown.length)];
        }
        if (visible.length > 0) {
            return visible[randomInt(visible.length)];
        }
        return undefined;
    }

    /**
     * Random delay generator
     * @returns a random delay between minDelayMilliseconds and maxDelayMilliseconds
     */
    function randomDelay(): number {
        return minDelayMilliseconds + Math.random() * (maxDelayMilliseconds - minDelayMilliseconds);
    }
}

/**
 * Random positive integer generator
 * 
 * @param max a positive integer which is the upper bound of the generated number
 * @returns a random integer >= 0 and < max
 */
function randomInt(max: number): number {
    return Math.floor(Math.random() * max);
}

/**
 * @param milliseconds duration to wait
 * @returns a promise that fulfills no less than `milliseconds` after timeout() was called
 */
async function timeout(milliseconds: number): Promise<void> {
    const { promise, resolve } = Promise.withResolvers<void>();
    setTimeout(resolve, milliseconds);
    return promise;
}

void simulationMain();
