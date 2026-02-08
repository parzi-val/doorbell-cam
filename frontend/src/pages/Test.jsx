import { useState, useEffect, useRef } from 'react';
import { Play, Square, Film, Activity, Shield, Wifi, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import clsx from 'clsx';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Test = () => {
    const [videos, setVideos] = useState([]);
    const [selectedVideo, setSelectedVideo] = useState("");
    const [simulating, setSimulating] = useState(false);
    const [metadata, setMetadata] = useState(null);
    const [connected, setConnected] = useState(false);
    const [history, setHistory] = useState([]);

    const wsRef = useRef(null);
    const imgRef = useRef(null);
    const historyRef = useRef([]); // Use ref for performance to avoid dependency loops in effect

    // Fetch Videos on Mount
    useEffect(() => {
        fetchVideos();
        // Ensure simulation is stopped on mount
        axios.post('http://localhost:8000/api/test/stop').catch(console.error);
    }, []);

    const fetchVideos = async () => {
        try {
            const res = await axios.get('http://localhost:8000/api/test/videos');
            setVideos(res.data);
            if (res.data.length > 0) setSelectedVideo(res.data[0]);
        } catch (e) {
            console.error("Failed to fetch videos", e);
        }
    };

    // WebSocket Connection
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);
        ws.onclose = () => setConnected(false);

        ws.onmessage = async (event) => {
            if (event.data instanceof Blob) {
                const url = URL.createObjectURL(event.data);
                if (imgRef.current) {
                    if (imgRef.current.src && imgRef.current.src.startsWith('blob:')) {
                        URL.revokeObjectURL(imgRef.current.src);
                    }
                    imgRef.current.src = url;
                }
            } else {
                try {
                    const data = JSON.parse(event.data);
                    setMetadata(data);
                    // Update History
                    const now = new Date().toLocaleTimeString();
                    const point = {
                        time: now,
                        intent: data.intent_score,
                        threat: data.threat_level === "THREAT" ? 1.0 : data.threat_level === "SUSPICIOUS" ? 0.5 : 0.0,
                        ...data.signals
                    };

                    // Keep last 100 points
                    const newHistory = [...historyRef.current, point].slice(-100);
                    historyRef.current = newHistory;
                    setHistory(newHistory);

                } catch (e) {
                    console.error("Error parsing metadata", e);
                }
            }
        };

        return () => {
            if (wsRef.current) wsRef.current.close();
        };
    }, []);

    const handleStart = async () => {
        if (!selectedVideo) return;
        try {
            await axios.post('http://localhost:8000/api/test/start', { filename: selectedVideo });
            setSimulating(true);
        } catch (e) {
            console.error("Failed to start simulation", e);
        }
    };

    const handleStop = async () => {
        try {
            await axios.post('http://localhost:8000/api/test/stop');
            setSimulating(false);
            setMetadata(null);
        } catch (e) {
            console.error("Failed to stop simulation", e);
        }
    };

    const intentScore = metadata?.intent_score || 0;
    const threatLevel = metadata?.threat_level || "WAITING";
    const isThreat = threatLevel === "THREAT" || threatLevel === "SUSPICIOUS";

    return (
        <div className="flex flex-col h-[calc(100vh-theme(spacing.24))] gap-4 p-4">

            {/* TOP ROW: Video & Controls */}
            <div className="flex-1 flex gap-4 min-h-0">

                {/* 1. Main Video Player */}
                <div className="flex-1 bg-black rounded-2xl overflow-hidden relative border border-border flex items-center justify-center shadow-lg">
                    <img
                        ref={imgRef}
                        alt="Simulation Stream"
                        className="w-full h-full object-contain"
                    />
                    <div className="absolute top-4 left-4">
                        <span className={clsx(
                            "px-3 py-1 rounded-full text-xs font-bold flex items-center gap-2 shadow-sm bg-white/90 backdrop-blur-sm",
                            simulating ? "text-accent-blue" : "text-secondary"
                        )}>
                            {simulating ? "SIMULATION RUNNING" : "LIVE CAMERA (IDLE)"}
                        </span>
                    </div>
                </div>

                {/* 2. Compact Controls & Metrics */}
                <div className="w-[340px] flex flex-col gap-3">

                    {/* Control Panel */}
                    <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                        <h2 className="text-sm font-bold text-primary mb-3 flex items-center gap-2">
                            <Film size={16} className="text-accent-blue" /> Controls
                        </h2>

                        <div className="flex flex-col gap-3">
                            <select
                                className="w-full p-2.5 rounded-lg border border-border bg-slate-50 text-sm font-medium focus:ring-2 focus:ring-accent-blue/20 outline-none"
                                value={selectedVideo}
                                onChange={(e) => setSelectedVideo(e.target.value)}
                                disabled={simulating}
                            >
                                {videos.length === 0 && <option>No videos found</option>}
                                {videos.map(v => <option key={v} value={v}>{v}</option>)}
                            </select>

                            <div className="grid grid-cols-2 gap-2">
                                <button
                                    onClick={handleStart}
                                    disabled={simulating || !selectedVideo}
                                    className={clsx(
                                        "py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-2 transition-all",
                                        simulating
                                            ? "bg-slate-100 text-secondary cursor-not-allowed"
                                            : "bg-primary text-white hover:bg-primary/90 shadow-md shadow-primary/20"
                                    )}
                                >
                                    <Play size={14} fill="currentColor" /> Play
                                </button>

                                <button
                                    onClick={handleStop}
                                    disabled={!simulating}
                                    className={clsx(
                                        "py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-2 transition-all",
                                        !simulating
                                            ? "bg-slate-100 text-secondary cursor-not-allowed"
                                            : "bg-accent-red text-white hover:bg-accent-red/90 shadow-md shadow-accent-red/20"
                                    )}
                                >
                                    <Square size={14} fill="currentColor" /> Stop
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Threat Metrics */}
                    <div className="bg-card p-5 rounded-2xl border border-border shadow-sm flex-1 flex flex-col justify-center">
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-bold text-secondary uppercase">Threat Level</span>
                        </div>
                        <div className="flex items-baseline gap-3 mb-4">
                            <span className={clsx(
                                "text-4xl font-black tracking-tight",
                                isThreat ? "text-accent-red animate-pulse" : "text-primary"
                            )}>
                                {threatLevel}
                            </span>
                            <span className="text-2xl font-mono font-bold text-secondary">
                                {intentScore.toFixed(2)}
                            </span>
                        </div>

                        <div className="space-y-3">
                            <div>
                                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                        className={clsx(
                                            "h-full transition-all duration-300",
                                            intentScore > 0.6 ? "bg-accent-red" : intentScore > 0.4 ? "bg-accent-orange" : "bg-accent-green"
                                        )}
                                        style={{ width: `${Math.min(intentScore * 100, 100)}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                </div>
            </div>

            {/* BOTTOM ROW: Combined Analytics Graph */}
            <div className="h-1/2 bg-card p-4 rounded-2xl border border-border shadow-sm flex flex-col min-h-0">
                <h3 className="text-sm font-bold text-primary mb-2 flex items-center gap-2">
                    <Activity size={16} className="text-primary" /> Real-time Analytics Overlay
                </h3>
                <div className="flex-1 min-h-0 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={history}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                            <XAxis dataKey="time" hide />

                            {/* Left Axis: Intent (0-1) */}
                            <YAxis yAxisId="left" domain={[0, 1]} orientation="left" stroke="#94a3b8" fontSize={11} tickFormatter={(val) => val.toFixed(1)} />

                            {/* Right Axis: Signals (Auto) */}
                            <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" fontSize={11} />

                            <Tooltip
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: '12px' }}
                            />
                            <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />

                            {/* Main Metrics (Left Axis) */}
                            <Line yAxisId="left" type="monotone" dataKey="intent" stroke="#2563eb" strokeWidth={2} dot={false} name="Intent" isAnimationActive={false} />
                            <Line yAxisId="left" type="step" dataKey="threat" stroke="#ef4444" strokeWidth={2} dot={false} name="Threat" isAnimationActive={false} />

                            {/* Signals (Right Axis) */}
                            <Line yAxisId="right" type="monotone" dataKey="motion_E" stroke="#f97316" dot={false} strokeWidth={1.5} name="Motion Energy" isAnimationActive={false} />
                            <Line yAxisId="right" type="monotone" dataKey="loitering_score" stroke="#eab308" dot={false} strokeWidth={2} name="Loitering" isAnimationActive={false} />
                            <Line yAxisId="right" type="monotone" dataKey="head_yaw_rate" stroke="#8b5cf6" dot={false} strokeWidth={1.5} name="Head Yaw" isAnimationActive={false} />
                            <Line yAxisId="right" type="monotone" dataKey="movinet_pressure" stroke="#ec4899" dot={false} strokeWidth={1} name="Pressure" isAnimationActive={false} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

        </div>
    );
};

export default Test;
