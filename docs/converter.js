/**
 * DXF to XYZ Web Conversion Engine
 * Implements voxel thinning and coordinate transformation logic in JavaScript.
 */

class DXFConverter {
    constructor() {
        this.points = [];
        this.options = {
            dedupe: true,
            dedupeEpsilon: 1e-6,
            voxelSize: null,
            scale: 1.0,
            centerOnOrigin: false,
            swapYZ: false,
            flipX: false,
            flipY: false,
            flipZ: false
        };
    }

    reset() {
        this.points = [];
    }

    /**
     * Extracts raw points from DXF entities.
     */
    extractPoints(entities) {
        const points = [];
        const entityCounts = {};

        const addPoint = (p) => {
            if (p && typeof p.x === 'number') {
                points.push([p.x, p.y, p.z || 0]);
            }
        };

        entities.forEach(entity => {
            const type = entity.type;
            entityCounts[type] = (entityCounts[type] || 0) + 1;

            switch (type) {
                case 'POINT':
                    addPoint(entity.position);
                    break;
                case 'LINE':
                    entity.vertices.forEach(v => addPoint(v));
                    break;
                case '3DFACE':
                    entity.vertices.forEach(v => addPoint(v));
                    break;
                case 'LWPOLYLINE':
                case 'POLYLINE':
                    if (entity.vertices) {
                        entity.vertices.forEach(v => addPoint(v));
                    }
                    break;
                case 'CIRCLE':
                case 'ARC':
                    // Sample points around the perimeter
                    this.sampleCircle(entity, points);
                    break;
                case 'SPLINE':
                    // Just take control points for now as a simple fallback
                    if (entity.controlPoints) {
                        entity.controlPoints.forEach(v => addPoint(v));
                    }
                    break;
            }
        });

        return { points, entityCounts };
    }

    sampleCircle(entity, points) {
        const center = entity.center;
        const radius = entity.radius;
        const startAngle = (entity.startAngle || 0) * (Math.PI / 180);
        const endAngle = (entity.endAngle !== undefined ? entity.endAngle : 360) * (Math.PI / 180);
        
        // Approximate arc with segments (0.05 units roughly)
        const circumference = radius * (endAngle - startAngle);
        const steps = Math.max(8, Math.ceil(circumference / 0.05));
        
        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const angle = startAngle + t * (endAngle - startAngle);
            points.push([
                center.x + radius * Math.cos(angle),
                center.y + radius * Math.sin(angle),
                center.z || 0
            ]);
        }
    }

    /**
     * Core processing logic: Dedupe, Thin, Transform.
     */
    process(rawPoints, options) {
        let pts = rawPoints;
        const countIn = pts.length;

        if (countIn === 0) {
            return { points: [], countIn: 0, countOut: 0 };
        }

        // 1. Dedupe / Initial Voxel Thin
        if (options.dedupe) {
            pts = this.voxelThin(pts, options.dedupeEpsilon || 1e-6);
        }
        const countAfterDedupe = pts.length;

        // 2. Voxel Thinning
        if (options.voxelSize && options.voxelSize > 0) {
            pts = this.voxelThin(pts, options.voxelSize);
        }

        // 3. Transformations
        let processed = pts.map(p => {
            let [x, y, z] = p;

            // Scale
            if (options.scale !== 1.0) {
                x *= options.scale;
                y *= options.scale;
                z *= options.scale;
            }

            // Flips
            if (options.flipX) x = -x;
            if (options.flipY) y = -y;
            if (options.flipZ) z = -z;

            // Swap YZ
            if (options.swapYZ) {
                const temp = y;
                y = z;
                z = temp;
            }

            return [x, y, z];
        });

        // 4. Center on Origin
        if (options.centerOnOrigin && processed.length > 0) {
            const sums = processed.reduce((acc, p) => [acc[0] + p[0], acc[1] + p[1], acc[2] + p[2]], [0, 0, 0]);
            const centroid = [sums[0] / processed.length, sums[1] / processed.length, sums[2] / processed.length];
            processed = processed.map(p => [p[0] - centroid[0], p[1] - centroid[1], p[2] - centroid[2]]);
        }

        // Calculate bounds
        const bounds = this.calculateBounds(processed);

        return {
            points: processed,
            bounds,
            countIn,
            countAfterDedupe,
            countOut: processed.length
        };
    }

    voxelThin(pts, leaf) {
        const seen = new Map();
        const result = [];

        pts.forEach(p => {
            const kx = Math.floor(p[0] / leaf);
            const ky = Math.floor(p[1] / leaf);
            const kz = Math.floor(p[2] / leaf);
            const key = `${kx},${ky},${kz}`;

            if (!seen.has(key)) {
                seen.set(key, true);
                result.push(p);
            }
        });

        return result;
    }

    calculateBounds(pts) {
        if (pts.length === 0) return { min: [0, 0, 0], max: [0, 0, 0], span: 0 };

        let min = [...pts[0]];
        let max = [...pts[0]];

        pts.forEach(p => {
            for (let i = 0; i < 3; i++) {
                if (p[i] < min[i]) min[i] = p[i];
                if (p[i] > max[i]) max[i] = p[i];
            }
        });

        const span = Math.sqrt(
            Math.pow(max[0] - min[0], 2) +
            Math.pow(max[1] - min[1], 2) +
            Math.pow(max[2] - min[2], 2)
        );

        return { min, max, span };
    }

    formatXYZ(pts) {
        return pts.map(p => p.map(c => c.toFixed(4)).join(' ')).join('\n');
    }
}

export default DXFConverter;
