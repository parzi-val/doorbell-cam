import { useState, useEffect, useRef } from 'react';
import { AlertTriangle, Shield, Activity, Wifi, WifiOff } from 'lucide-react';
import clsx from 'clsx';
import axios from 'axios';

const Live = () => {
    const [connected, setConnected] = useState(false);
    const [imgSrc, setImgSrc] = useState(null);
    const [metadata, setMetadata] = useState(null);
    const wsRef = useRef(null);
    const imgRef = useRef(null);

    useEffect(() => {
        // Force server to Live Webcam mode on mount
        axios.post('http://localhost:8000/api/live/start').catch(e => console.error("Failed to switch to live mode", e));

        // Connect to WebSocket
        const ws = new WebSocket('ws://localhost:8000/ws');
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("Connected to Stream");
            setConnected(true);
        };

        ws.onclose = () => {
            console.log("Disconnected from Stream");
            setConnected(false);
        };

        ws.onmessage = async (event) => {
            // Check data type
            if (event.data instanceof Blob) {
                // It's a frame
                // console.log("Blob size:", event.data.size);
                const url = URL.createObjectURL(event.data);

                // Revoke previous URL to avoid memory leak
                if (imgRef.current) {
                    // We can't revoke immediately if it hasn't rendered?
                    // Actually React state update is async.
                    // Better: raw DOM manipulation for high freq video?
                    // Or just rely on browser GC if we use one object URL?
                    // Let's use simple state for now, but revoke inside the setter?
                    // No, "previous" state is hard to get synchronously here.
                    // Let's try direct ref update for image src to avoid React render cycle overhead for frames
                    if (imgRef.current.src && imgRef.current.src.startsWith('blob:')) {
                        URL.revokeObjectURL(imgRef.current.src);
                    }
                    imgRef.current.src = url;
                }
            } else {
                // It's JSON metadata
                try {
                    const data = JSON.parse(event.data);
                    setMetadata(data);
                } catch (e) {
                    console.error("Error parsing metadata", e);
                }
            }
        };

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);

    const intentScore = metadata?.intent_score || 0;
    const threatLevel = metadata?.threat_level || "WAITING";
    const isThreat = threatLevel === "THREAT" || threatLevel === "SUSPICIOUS";

    // Helper to format signal name
    const formatName = (key) => {
        return key.replace(/_/g, ' ').toUpperCase();
    };

    return (
        <div className="flex h-[calc(100vh-theme(spacing.24))] gap-6">
            {/* Main Video Feed */}
            <div className="flex-1 bg-black rounded-2xl overflow-hidden relative border border-border flex items-center justify-center">
                {connected ? (
                    <img
                        ref={imgRef}
                        alt="Live Stream"
                        className="w-full h-full object-contain"
                    />
                ) : (
                    <div className="flex flex-col items-center text-secondary gap-4">
                        <WifiOff size={48} />
                        <span className="text-xl">Connecting to Camera Source...</span>
                    </div>
                )}

                {/* Overlay Status */}
                <div className="absolute top-4 left-4 flex gap-2">
                    <span className={clsx(
                        "px-3 py-1 rounded-full text-xs font-bold flex items-center gap-2 shadow-sm",
                        connected ? "bg-accent-green/20 text-accent-green bg-white/90" : "bg-red-500/20 text-red-500 bg-white/90"
                    )}>
                        <div className={clsx("w-2 h-2 rounded-full", connected ? "bg-accent-green" : "bg-red-500")} />
                        {connected ? "LIVE" : "OFFLINE"}
                    </span>
                    {metadata?.signals?.weapon_score > 0.6 && (
                        <span className="bg-accent-red text-white px-3 py-1 rounded-full text-xs font-bold flex items-center gap-2 shadow-sm animate-pulse">
                            <AlertTriangle size={14} /> WEAPON DETECTED
                        </span>
                    )}
                </div>
            </div>

            {/* Right Sidebar - Analytics */}
            <div className="w-96 flex flex-col gap-6">

                {/* Top Card: Intent */}
                <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
                    <h2 className="text-secondary text-sm font-bold uppercase tracking-wider mb-2 flex items-center gap-2">
                        <Shield size={16} /> Threat Assessment
                    </h2>
                    <div className="flex items-baseline justify-between mb-4">
                        <span className={clsx(
                            "text-4xl font-black",
                            isThreat ? "text-accent-red" : "text-primary"
                        )}>
                            {threatLevel}
                        </span>
                        <span className="text-2xl font-mono text-secondary">
                            {intentScore.toFixed(2)}
                        </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                            className={clsx(
                                "h-full transition-all duration-300",
                                intentScore > 0.6 ? "bg-accent-red" : intentScore > 0.4 ? "bg-accent-orange" : "bg-accent-green"
                            )}
                            style={{ width: `${Math.min(intentScore * 100, 100)}%` }}
                        />
                    </div>
                </div>

                {/* Signal List */}
                <div className="bg-card flex-1 rounded-2xl border border-border shadow-sm overflow-hidden flex flex-col">
                    <div className="p-4 border-b border-border bg-slate-50">
                        <h3 className="text-sm font-bold text-primary flex items-center gap-2">
                            <Activity size={16} className="text-accent-orange" /> Real-time Signals
                        </h3>
                    </div>

                    <div className="flex-1 overflow-y-auto p-2 scrollbar-hide">
                        {metadata && metadata.signals ? (
                            <div className="grid grid-cols-1 gap-1">
                                {Object.entries(metadata.signals).map(([key, val]) => (
                                    <div key={key} className="flex justify-between items-center p-3 hover:bg-slate-50 rounded-lg transition-colors border border-transparent hover:border-slate-100">
                                        <span className="text-xs font-medium text-secondary/80">{formatName(key)}</span>
                                        <span className={clsx(
                                            "font-mono text-sm font-bold",
                                            val > 0.5 && "text-primary",
                                            val > 0.8 && "text-accent-orange"
                                        )}>
                                            {val.toFixed(3)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-full text-secondary text-sm">
                                Waiting for data...
                            </div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
};

export default Live;
