import { ContactShadows, Edges, Grid, Html, Line, OrbitControls, OrthographicCamera, PerspectiveCamera } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { outcomePoint, type DecodedReplay } from "../../data/replay";
import type { Scene, ScenePart } from "../../data/types";

export type CameraMode = "three" | "side" | "follow";

export interface Marks {
  past?: { value: number[]; faint?: boolean }[];
  prediction?: number[] | null;
  observed?: number[] | null;
  truth?: number[] | null;
  goal?: number[] | null;
  verdict?: "hit" | "miss" | null;
}

interface Props {
  scene: Scene;
  replay?: DecodedReplay | null;
  replayKey?: string;
  rate?: number;
  loop?: boolean;
  marks?: Marks;
  camera?: CameraMode;
  partLabels?: Record<string, string>;
  highlight?: string[];
}

const INK = "#14181b";
const SIGNAL = "#f0541a";
const TRUTH = "#1b58c2";
const HIT = "#16804a";
const MISS = "#c42d25";

const MATERIAL: Record<string, string> = {
  wood: "#cfc2ab",
  steel: "#a3aab1",
  aluminium: "#cdd2d6",
  rubber: "#3d4146",
  concrete: "#c0c0ba",
};
const HIDDEN = "#2f3439";

const AXIS: Record<string, number> = { x: 0, y: 1, z: 2 };

function geometryFor(p: ScenePart): THREE.BufferGeometry {
  const s = p.size;
  switch (p.shape) {
    case "box":
      return new THREE.BoxGeometry(2 * s[0], 2 * s[1], 2 * s[2]);
    case "sphere":
      return new THREE.SphereGeometry(s[0], 32, 20);
    case "capsule":
      return new THREE.CapsuleGeometry(s[0], 2 * s[1], 8, 24).rotateX(Math.PI / 2);
    case "cylinder":
      return new THREE.CylinderGeometry(s[0], s[0], 2 * s[1], 32).rotateX(Math.PI / 2);
    default: {
      const never: never = p.shape;
      throw new Error(`shape ${String(never)}`);
    }
  }
}

function bounds(scene: Scene): { center: THREE.Vector3; size: THREE.Vector3 } {
  const box = new THREE.Box3();
  for (const p of scene.parts) {
    const r = Math.max(...p.size) * (p.shape === "box" ? 1.0 : 1.2);
    box.expandByPoint(new THREE.Vector3(p.pos[0] - r, p.pos[1] - r, p.pos[2] - r));
    box.expandByPoint(new THREE.Vector3(p.pos[0] + r, p.pos[1] + r, p.pos[2] + r));
  }
  for (const corner of [0, 1]) {
    const pt = outcomePoint(scene, scene.goal_space.map((g) => g[corner]));
    if (pt) box.expandByPoint(new THREE.Vector3(...pt));
  }
  box.expandByPoint(new THREE.Vector3(box.min.x, box.min.y, 0));
  return { center: box.getCenter(new THREE.Vector3()), size: box.getSize(new THREE.Vector3()) };
}

/** Horizontal axis the outcome runs along, and the one across it (the side-view direction). */
function axes(scene: Scene): { along: THREE.Vector3; across: THREE.Vector3 } {
  const a = scene.outcome.axes.find((x) => x !== "z") ?? "x";
  const along = new THREE.Vector3();
  along.setComponent(AXIS[a], 1);
  const across = a === "x" ? new THREE.Vector3(0, -1, 0) : new THREE.Vector3(1, 0, 0);
  return { along, across };
}

function Parts({ scene, replay, clockRef, refs, labels, highlight }: {
  scene: Scene;
  replay?: DecodedReplay | null;
  clockRef: React.MutableRefObject<{ t: number }>;
  refs: React.MutableRefObject<Record<string, THREE.Object3D | null>>;
  labels?: Record<string, string>;
  highlight?: string[];
}) {
  const geoms = useMemo(() => Object.fromEntries(scene.parts.map((p) => [p.name, geometryFor(p)])), [scene]);

  useEffect(() => {
    if (replay) return;
    for (const p of scene.parts) {
      const o = refs.current[p.name];
      o?.position.set(p.pos[0], p.pos[1], p.pos[2]);
      o?.quaternion.set(p.quat[0], p.quat[1], p.quat[2], p.quat[3]);
    }
  }, [replay, scene, refs]);

  useFrame(() => {
    if (!replay || replay.frames === 0) return;
    const t = Math.min(clockRef.current.t, playLength(replay));
    const f = Math.min(replay.frames - 1, Math.floor(t * replay.fps));
    const stride = replay.parts.length * 7;
    replay.parts.forEach((name, j) => {
      const o = refs.current[name];
      if (!o) return;
      const k = f * stride + j * 7;
      const d = replay.data;
      o.position.set(d[k], d[k + 1], d[k + 2]);
      o.quaternion.set(d[k + 3], d[k + 4], d[k + 5], d[k + 6]);
    });
  });

  return (
    <group>
      {scene.parts.map((p) => {
        const color = p.hidden ? HIDDEN : (MATERIAL[p.material] ?? "#b8bec3");
        const glow = highlight?.includes(p.name);
        return (
          <group
            key={p.name}
            ref={(o) => {
              refs.current[p.name] = o;
            }}
            position={p.pos as [number, number, number]}
            quaternion={new THREE.Quaternion(p.quat[0], p.quat[1], p.quat[2], p.quat[3])}
          >
            <mesh geometry={geoms[p.name]}>
              <meshStandardMaterial color={color} roughness={0.86} metalness={p.material === "steel" ? 0.15 : 0} />
              <Edges color={glow ? SIGNAL : INK} threshold={18} lineWidth={glow ? 2 : 1} />
            </mesh>
            {labels?.[p.name] && (
              <Html center distanceFactor={undefined} position={[0, 0, Math.max(...p.size) + 0.04]} zIndexRange={[10, 0]}>
                <div className="part-label truth">{labels[p.name]}</div>
              </Html>
            )}
          </group>
        );
      })}
    </group>
  );
}

function FloorMarks({ scene, marks, appearAt, clockRef }: {
  scene: Scene;
  marks: Marks;
  appearAt: number;
  clockRef: React.MutableRefObject<{ t: number }>;
}) {
  const tol = scene.tolerance;
  const { across } = axes(scene);
  const u = useMemo(() => Math.max(0.004, 0.006 * bounds(scene).size.length()), [scene]);
  const landing = useRef<THREE.Group>(null);
  useFrame(() => {
    if (landing.current) landing.current.visible = clockRef.current.t >= appearAt;
  });
  const pred = outcomePoint(scene, marks.prediction);
  const obs = outcomePoint(scene, marks.observed);
  const truth = outcomePoint(scene, marks.truth);
  const goal = outcomePoint(scene, marks.goal);
  const lo = outcomePoint(scene, scene.goal_space.map((g) => g[0]));
  const hi = outcomePoint(scene, scene.goal_space.map((g) => g[1]));
  const halfWidth = 0.09;
  const side = across.clone().multiplyScalar(halfWidth);
  const flat = new THREE.Euler(0, 0, 0);
  const verdictColor = marks.verdict === "hit" ? HIT : marks.verdict === "miss" ? MISS : INK;

  return (
    <group>
      {lo && hi && (
        <>
          <Line points={[new THREE.Vector3(...lo).add(side), new THREE.Vector3(...lo).sub(side)]} color={INK} lineWidth={1} />
          <Line points={[new THREE.Vector3(...hi).add(side), new THREE.Vector3(...hi).sub(side)]} color={INK} lineWidth={1} />
          <Line
            points={[new THREE.Vector3(...lo), new THREE.Vector3(...hi)]}
            color={INK}
            lineWidth={1}
            dashed
            dashSize={0.02}
            gapSize={0.015}
          />
        </>
      )}
      {(marks.past ?? []).map((m, i) => {
        const p = outcomePoint(scene, m.value);
        return p ? (
          <mesh key={i} position={[p[0], p[1], 0.0015]} rotation={flat}>
            <circleGeometry args={[u * 0.9, 16]} />
            <meshBasicMaterial color={INK} transparent opacity={m.faint ? 0.28 : 0.45} />
          </mesh>
        ) : null;
      })}
      {goal && (
        <mesh position={[goal[0], goal[1], 0.001]}>
          <circleGeometry args={[tol, 48]} />
          <meshBasicMaterial color={HIT} transparent opacity={0.16} />
        </mesh>
      )}
      {goal && (
        <mesh position={[goal[0], goal[1], 0.0012]}>
          <ringGeometry args={[tol - 0.002, tol, 64]} />
          <meshBasicMaterial color={HIT} />
        </mesh>
      )}
      {pred && (
        <mesh position={[pred[0], pred[1], 0.003]}>
          <ringGeometry args={[tol * 0.78, tol, 64]} />
          <meshBasicMaterial color={SIGNAL} transparent opacity={0.9} />
        </mesh>
      )}
      <group ref={landing}>
        {obs && (
          <>
            <mesh position={[obs[0], obs[1], 0.004]}>
              <circleGeometry args={[u * 1.6, 24]} />
              <meshBasicMaterial color={verdictColor} />
            </mesh>
            <mesh position={[obs[0], obs[1], u * 7]} rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[u * 0.3, u * 0.3, u * 14, 8]} />
              <meshBasicMaterial color={verdictColor} />
            </mesh>
          </>
        )}
        {pred && obs && (
          <Line
            points={[new THREE.Vector3(pred[0], pred[1], 0.005), new THREE.Vector3(obs[0], obs[1], 0.005)]}
            color={SIGNAL}
            lineWidth={1.5}
          />
        )}
        {truth && (
          <group position={[truth[0], truth[1], 0.005]}>
            <mesh rotation={[0, 0, Math.PI / 4]}>
              <planeGeometry args={[u * 5, u * 0.7]} />
              <meshBasicMaterial color={TRUTH} />
            </mesh>
            <mesh rotation={[0, 0, -Math.PI / 4]}>
              <planeGeometry args={[u * 5, u * 0.7]} />
              <meshBasicMaterial color={TRUTH} />
            </mesh>
          </group>
        )}
      </group>
    </group>
  );
}

function CameraRig({ scene, mode, refs }: {
  scene: Scene;
  mode: CameraMode;
  refs: React.MutableRefObject<Record<string, THREE.Object3D | null>>;
}) {
  const { center, size } = useMemo(() => bounds(scene), [scene]);
  const { along, across } = useMemo(() => axes(scene), [scene]);
  const viewport = useThree((s) => s.size);
  const controls = useRef<React.ComponentRef<typeof OrbitControls>>(null);
  const fov = 34;
  const view = useMemo(() => {
    const radius = Math.max(0.3, 0.5 * size.length());
    const target = center.clone().setZ(Math.max(0.1, center.z * 0.6));
    const aspect = viewport.width / Math.max(1, viewport.height);
    const fit = radius / Math.sin(((fov / 2) * Math.PI) / 180) / Math.min(1, aspect);
    const dir = across.clone().multiplyScalar(0.82).add(along.clone().multiplyScalar(-0.3)).add(new THREE.Vector3(0, 0, 0.42)).normalize();
    const extentH = Math.abs(along.x) ? size.x : size.y;
    return {
      target,
      threeQuarter: target.clone().add(dir.multiplyScalar(fit * 0.78)).toArray(),
      side: target.clone().add(across.clone().multiplyScalar(radius * 6)).toArray(),
      zoom: Math.min(viewport.width / (extentH * 1.15 || 1), viewport.height / (Math.max(size.z, 0.3) * 1.6 || 1)),
    };
  }, [center, size, across, along, viewport.width, viewport.height]);


  useFrame(() => {
    if (mode !== "follow" || !controls.current) return;
    const ball = refs.current[scene.outcome.part];
    if (!ball) return;
    const want = ball.position.clone();
    controls.current.target.lerp(want, 0.08);
    controls.current.update();
  });

  return (
    <>
      {mode === "side" ? (
        <OrthographicCamera makeDefault up={[0, 0, 1]} position={view.side} zoom={view.zoom} near={0.01} far={50} />
      ) : (
        <PerspectiveCamera makeDefault up={[0, 0, 1]} position={view.threeQuarter} fov={fov} near={0.01} far={60} />
      )}
      <OrbitControls
        key={mode}
        ref={controls}
        makeDefault
        target={view.target}
        enableDamping
        dampingFactor={0.12}
        enableRotate={mode !== "side"}
      />
    </>
  );
}

export function DeviceScene({ scene, replay, replayKey, rate = 1, loop = true, marks = {}, camera = "three", partLabels, highlight }: Props) {
  const refs = useRef<Record<string, THREE.Object3D | null>>({});
  const clockRef = useRef({ t: 0 });
  useEffect(() => {
    clockRef.current.t = 0;
  }, [replayKey, replay]);
  const appearAt = replay ? Math.max(0.05, replay.tOutcome) : 0;
  const { center } = useMemo(() => bounds(scene), [scene]);

  return (
    <Canvas dpr={[1, 2]} gl={{ antialias: true, preserveDrawingBuffer: true }} style={{ background: "transparent" }}>
      <ambientLight intensity={0.85} />
      <directionalLight position={[-2, -3, 5]} intensity={1.25} />
      <directionalLight position={[3, 2, 2]} intensity={0.35} />
      <ReplayClock clockRef={clockRef} replay={replay} rate={rate} loop={loop} />
      <Parts scene={scene} replay={replay} clockRef={clockRef} refs={refs} labels={partLabels} highlight={highlight} />
      <FloorMarks scene={scene} marks={marks} appearAt={appearAt} clockRef={clockRef} />
      {replay && <Trail replay={replay} part={scene.outcome.part} />}
      <mesh position={[center.x, center.y, -0.0005]}>
        <planeGeometry args={[12, 12]} />
        <meshBasicMaterial color="#fbfcfc" />
      </mesh>
      <Grid
        rotation={[Math.PI / 2, 0, 0]}
        position={[center.x, center.y, 0]}
        cellSize={0.05}
        cellThickness={0.6}
        cellColor="#dfe4e7"
        sectionSize={0.25}
        sectionThickness={1}
        sectionColor="#c3cacf"
        fadeDistance={7}
        fadeStrength={1.5}
        infiniteGrid
      />
      <ContactShadows rotation={[Math.PI / 2, 0, 0]} position={[center.x, center.y, 0.0008]} scale={4} blur={2.4} opacity={0.35} far={1.2} />
      <CameraRig scene={scene} mode={camera} refs={refs} />
    </Canvas>
  );
}

/** Seconds into the replay; it holds the last frame briefly before looping. */
function ReplayClock({ clockRef, replay, rate, loop }: {
  clockRef: React.MutableRefObject<{ t: number }>;
  replay?: DecodedReplay | null;
  rate: number;
  loop: boolean;
}) {
  useFrame((_, delta) => {
    if (!replay) {
      clockRef.current.t = 1e9;
      return;
    }
    const length = playLength(replay);
    clockRef.current.t += Math.min(delta, 0.1) * rate;
    if (clockRef.current.t > length + HOLD_S) clockRef.current.t = loop ? 0 : length + HOLD_S;
  });
  return null;
}

/** Path of the outcome part over the replay, up to shortly after the outcome. */
function Trail({ replay, part }: { replay: DecodedReplay; part: string }) {
  const points = useMemo(() => {
    const j = replay.parts.indexOf(part);
    if (j < 0) return null;
    const last = Math.min(replay.frames - 1, Math.floor(playLength(replay) * replay.fps));
    const stride = replay.parts.length * 7;
    const pts: THREE.Vector3[] = [];
    for (let f = 0; f <= last; f++) {
      const k = f * stride + j * 7;
      pts.push(new THREE.Vector3(replay.data[k], replay.data[k + 1], replay.data[k + 2]));
    }
    return pts.length > 1 ? pts : null;
  }, [replay, part]);
  if (!points) return null;
  return <Line points={points} color={INK} lineWidth={1} transparent opacity={0.4} dashed dashSize={0.015} gapSize={0.01} />;
}

const HOLD_S = 1.4;
const AFTER_OUTCOME_S = 0.6;

/** A landing replay stops shortly after touchdown, before the ball rolls out of frame. */
function playLength(replay: DecodedReplay): number {
  const full = replay.frames / replay.fps;
  return replay.outcome ? Math.min(full, replay.tOutcome + AFTER_OUTCOME_S) : full;
}
