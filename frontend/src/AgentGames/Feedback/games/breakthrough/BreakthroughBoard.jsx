import React, { useRef, useEffect } from 'react';

const CANVAS_SIZE = 600;

const BreakthroughBoard = ({ gridSize, attackerTrail, defenderTrail, attackerPos, defenderPos, caught }) => {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const cell = CANVAS_SIZE / gridSize;

        // y is flipped so row 0 renders at the bottom
        const cx = (x) => (x + 0.5) * cell;
        const cy = (y) => CANVAS_SIZE - (y + 0.5) * cell;

        ctx.fillStyle = '#f8fafc';
        ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

        // Goal column
        ctx.fillStyle = 'rgba(34, 197, 94, 0.35)';
        ctx.fillRect((gridSize - 1) * cell, 0, cell, CANVAS_SIZE);

        const drawDot = (x, y, color, radius) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(cx(x), cy(y), radius, 0, Math.PI * 2);
            ctx.fill();
        };

        // Pale traces
        const traceRadius = Math.max(cell * 0.35, 1.5);
        attackerTrail.forEach(([x, y]) => drawDot(x, y, 'rgba(220, 38, 38, 0.18)', traceRadius));
        defenderTrail.forEach(([x, y]) => drawDot(x, y, 'rgba(37, 99, 235, 0.18)', traceRadius));

        // Current positions
        const dotRadius = Math.max(cell * 0.8, 4);
        if (defenderPos) drawDot(defenderPos[0], defenderPos[1], '#2563eb', dotRadius);
        if (attackerPos) drawDot(attackerPos[0], attackerPos[1], '#dc2626', dotRadius);

        if (caught && attackerPos) {
            ctx.strokeStyle = '#f59e0b';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.arc(cx(attackerPos[0]), cy(attackerPos[1]), dotRadius * 2.2, 0, Math.PI * 2);
            ctx.stroke();
        }

        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 1;
        ctx.strokeRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    }, [gridSize, attackerTrail, defenderTrail, attackerPos, defenderPos, caught]);

    return (
        <canvas
            ref={canvasRef}
            width={CANVAS_SIZE}
            height={CANVAS_SIZE}
            className="w-full max-w-[600px] mx-auto block border border-ui-light rounded-lg bg-white"
        />
    );
};

export default BreakthroughBoard;
