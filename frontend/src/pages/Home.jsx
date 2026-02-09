
import { useState, useEffect, useRef } from 'react';
import {
    Users,
    ShieldAlert,
    Lock,
    Unlock,
    Wifi,
    WifiOff,
    Activity,
    ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import EventCard from '../components/EventCard';
import VideoModal from '../components/VideoModal';
import toast from 'react-hot-toast';

// Mock Config
const WS_URL = 'ws://localhost:8000/ws';

const Home = () => {
    // State
    const [events, setEvents] = useState([]);
    const [metrics, setMetrics] = useState({
        totalVisits: 0,
        threats: 0,
        suspicious: 0
    });
    const [liveIntent, setLiveIntent] = useState(0.0);
    const [isLocked, setIsLocked] = useState(true);
    const [isOnline, setIsOnline] = useState(true);
    const [selectedEvent, setSelectedEvent] = useState(null);

    // WebSocket for Live Intent
    const ws = useRef(null);
    const lastAlertTime = useRef(0);

    useEffect(() => {
        // Fetch Events for Metrics & Recent List
        fetch('http://localhost:8000/api/events')
            .then(res => res.json())
            .then(data => {
                setEvents(data);

                // Calculate Metrics
                const threats = data.filter(e => e.final_level === 'THREAT' || e.trigger_level === 'THREAT').length;
                const suspicious = data.filter(e => e.final_level === 'SUSPICIOUS' || e.trigger_level === 'SUSPICIOUS').length;

                setMetrics({
                    totalVisits: data.length,
                    threats,
                    suspicious
                });
            })
            .catch(err => console.error("Failed to fetch events:", err));

        // Connect WebSocket
        ws.current = new WebSocket(WS_URL);

        ws.current.onopen = () => {
            console.log("Dashboard WS Connected");
            setIsOnline(true);
        };

        ws.current.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // Expecting metadata frame
                if (data.intent_score !== undefined) {
                    setLiveIntent(data.intent_score);

                    // High Intent Alert
                    if (data.intent_score > 0.7) {
                        const now = Date.now();
                        if (now - lastAlertTime.current > 5000) { // 5s debounce
                            toast.error(
                                <div>
                                    <b>High Intent Monitor</b>
                                    <div className="text-xs">{(data.intent_score * 100).toFixed(0)}% Threat Probability</div>
                                </div>,
                                { duration: 4000 }
                            );
                            lastAlertTime.current = now;
                        }
                    }
                }
            } catch (e) {
                // Ignore binary frames or errors
            }
        };

        ws.current.onclose = () => {
            console.log("Dashboard WS Disconnected");
            setIsOnline(false);
        };

        return () => {
            if (ws.current) ws.current.close();
        };
    }, []);

    // Helper for Intent Color
    const getIntentColor = (score) => {
        if (score > 0.8) return "text-accent-red";
        if (score > 0.5) return "text-accent-orange";
        return "text-accent-green";
    };

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            {/* Header / Status Bar */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-primary">Security Dashboard</h1>
                    <p className="text-secondary">Overview of system status and recent activity.</p>
                </div>

                <div className="flex gap-4">
                    {/* Door Status */}
                    <div
                        className={clsx(
                            "flex items-center gap-2 px-4 py-2 rounded-lg font-medium border transition-colors cursor-pointer",
                            isLocked
                                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                : "bg-amber-50 text-amber-700 border-amber-200"
                        )}
                        onClick={() => setIsLocked(!isLocked)}
                    >
                        {isLocked ? <Lock size={18} /> : <Unlock size={18} />}
                        <span>{isLocked ? "Door Locked" : "Door Unlocked"}</span>
                    </div>

                    {/* Cloud Status */}
                    <div className={clsx(
                        "flex items-center gap-2 px-4 py-2 rounded-lg font-medium border",
                        isOnline
                            ? "bg-blue-50 text-blue-700 border-blue-200"
                            : "bg-slate-100 text-slate-500 border-slate-200"
                    )}>
                        {isOnline ? <Wifi size={18} /> : <WifiOff size={18} />}
                        <span>{isOnline ? "Cloud Connected" : "Offline"}</span>
                    </div>
                </div>
            </div>

            {/* KPI Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Total Visits */}
                <div className="bg-card p-6 rounded-xl border border-border shadow-sm flex items-center gap-4">
                    <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
                        <Users size={24} />
                    </div>
                    <div>
                        <span className="text-sm text-secondary font-medium">Total Visits</span>
                        <div className="text-2xl font-bold text-primary">{metrics.totalVisits}</div>
                    </div>
                </div>

                {/* Threats */}
                <div className="bg-card p-6 rounded-xl border border-border shadow-sm flex items-center gap-4">
                    <div className="p-3 bg-red-50 text-accent-red rounded-lg">
                        <ShieldAlert size={24} />
                    </div>
                    <div>
                        <span className="text-sm text-secondary font-medium">Threats Detected</span>
                        <div className="text-2xl font-bold text-primary">{metrics.threats}</div>
                    </div>
                </div>

                {/* Suspicious */}
                <div className="bg-card p-6 rounded-xl border border-border shadow-sm flex items-center gap-4">
                    <div className="p-3 bg-orange-50 text-accent-orange rounded-lg">
                        <Activity size={24} />
                    </div>
                    <div>
                        <span className="text-sm text-secondary font-medium">Suspicious Activity</span>
                        <div className="text-2xl font-bold text-primary">{metrics.suspicious}</div>
                    </div>
                </div>

                {/* Live Intent */}
                <div className="bg-card p-6 rounded-xl border border-border shadow-sm flex items-center gap-4 relative overflow-hidden">
                    <div className={clsx("p-3 rounded-lg transition-colors",
                        liveIntent > 0.5 ? "bg-red-50 text-accent-red" : "bg-emerald-50 text-emerald-600"
                    )}>
                        <Activity size={24} className={clsx(liveIntent > 0.1 && "animate-pulse")} />
                    </div>
                    <div className="z-10">
                        <span className="text-sm text-secondary font-medium">Live Intent Score</span>
                        <div className={clsx("text-2xl font-bold font-mono transition-colors", getIntentColor(liveIntent))}>
                            {liveIntent.toFixed(2)}
                        </div>
                    </div>
                    {/* Background Bar */}
                    <div
                        className="absolute bottom-0 left-0 h-1 bg-current opacity-20 transition-all duration-300"
                        style={{ width: `${Math.min(100, liveIntent * 100)}%`, color: liveIntent > 0.5 ? '#ef4444' : '#10b981' }}
                    />
                </div>
            </div>

            {/* Recent Activity Section */}
            <div>
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold text-primary">Recent Activity</h2>
                    <Link to="/events" className="text-accent-green hover:underline flex items-center gap-1 text-sm font-medium">
                        View All <ArrowRight size={16} />
                    </Link>
                </div>

                {events.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                        {events.slice(0, 5).map(event => (
                            <EventCard
                                key={event.clip_id || event.timestamp}
                                event={event}
                                onClick={setSelectedEvent}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="bg-slate-50 border border-border border-dashed rounded-xl p-12 text-center text-secondary">
                        No recent activity recorded.
                    </div>
                )}
            </div>

            {/* Video Modal */}
            <VideoModal
                event={selectedEvent}
                onClose={() => setSelectedEvent(null)}
            />
        </div>
    );
};

export default Home;
