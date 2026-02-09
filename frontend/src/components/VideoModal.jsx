import { X, Check, ThumbsUp, ThumbsDown, Shield } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

const VideoModal = ({ event, onClose }) => {
    if (!event) return null;

    const date = new Date(event.timestamp * 1000);
    const videoSrc = `http://localhost:8000${event.video_url}`;

    const handleFeedback = async (type) => {
        try {
            const res = await fetch('http://localhost:8000/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    event_id: event.clip_id,
                    feedback_type: type
                })
            });
            const data = await res.json();

            // Show toast with conclusion
            toast.success(
                <div>
                    <b>Learning Report Generated</b>
                    <div className="text-xs mt-1 opacity-90">{data.conclusion}</div>
                </div>,
                { duration: 4000 }
            );
        } catch (err) {
            console.error(err);
            toast.error("Failed to record feedback");
        }
    };

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={onClose}>
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="bg-card w-full max-w-6xl h-[85vh] rounded-2xl overflow-hidden shadow-2xl flex flex-col md:flex-row border border-border"
                    onClick={e => e.stopPropagation()}
                >
                    {/* Video Section */}
                    <div className="flex-1 bg-black flex items-center justify-center relative">
                        <video
                            src={videoSrc}
                            controls
                            autoPlay
                            className="max-w-full max-h-full"
                        />
                        <button
                            onClick={onClose}
                            className="absolute top-4 right-4 p-2 bg-black/50 hover:bg-white/20 rounded-full text-white transition-colors"
                        >
                            <X size={24} />
                        </button>
                    </div>

                    {/* Info Section */}
                    <div className="w-full md:w-96 bg-card border-l border-border flex flex-col p-6 overflow-y-auto">
                        <div className="mb-6">
                            <h2 className={clsx(
                                "text-2xl font-bold mb-2",
                                event.final_level === 'THREAT' ? "text-accent-red" : "text-accent-orange"
                            )}>
                                {event.final_level}
                            </h2>
                            <p className="text-secondary text-sm">
                                {format(date, 'PPPP p')}
                            </p>
                        </div>

                        <div className="flex gap-2 flex-wrap mb-6">
                            <span className="bg-slate-100 border border-border px-3 py-1 rounded text-xs font-medium text-secondary">
                                ID: {event.clip_id || "N/A"}
                            </span>
                            {event.weapon_detected && (
                                <span className="bg-accent-red/10 text-accent-red border border-accent-red/20 px-3 py-1 rounded text-xs font-bold">
                                    WEAPON DETECTED
                                </span>
                            )}
                        </div>

                        {/* AI Summary */}
                        <div className="bg-slate-50 p-4 rounded-lg border border-border mb-6">
                            <h3 className="text-sm font-bold text-primary mb-2 flex items-center gap-2">
                                <Shield size={14} className="text-accent-green" /> AI Analysis
                            </h3>
                            <p className="text-sm text-secondary leading-relaxed">
                                {event.summary || "No summary available."}
                            </p>
                        </div>

                        {/* Stats */}
                        <div className="grid grid-cols-2 gap-4 mb-8">
                            <div className="bg-slate-100 p-3 rounded-lg border border-border">
                                <span className="text-xs text-secondary block mb-1">Max Intent</span>
                                <span className="text-lg font-mono font-bold text-primary">{event.max_intent.toFixed(2)}</span>
                            </div>
                            <div className="bg-slate-100 p-3 rounded-lg border border-border">
                                <span className="text-xs text-secondary block mb-1">Duration</span>
                                <span className="text-lg font-mono font-bold text-primary">{event.duration?.toFixed(1)}s</span>
                            </div>
                            <div className="bg-slate-100 p-3 rounded-lg border border-border">
                                <span className="text-xs text-secondary block mb-1">Weapon Conf</span>
                                <span className="text-lg font-mono font-bold text-primary">
                                    {event.signals_stats?.weapon_score ? (event.signals_stats.weapon_score.max * 100).toFixed(0) + '%' : 'N/A'}
                                </span>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="mt-auto grid grid-cols-2 gap-3">
                            <button
                                onClick={() => handleFeedback('accurate')}
                                className="col-span-1 py-3 bg-accent-green/10 text-accent-green hover:bg-accent-green/20 rounded-lg font-semibold text-sm transition-colors flex items-center justify-center gap-2"
                            >
                                <ThumbsUp size={16} /> Accurate
                            </button>
                            <button
                                onClick={() => handleFeedback('inaccurate')}
                                className="col-span-1 py-3 bg-accent-red/10 text-accent-red hover:bg-accent-red/20 rounded-lg font-semibold text-sm transition-colors flex items-center justify-center gap-2"
                            >
                                <ThumbsDown size={16} /> Inaccurate
                            </button>
                            <button className="col-span-2 py-3 bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 rounded-lg font-semibold text-sm transition-colors flex items-center justify-center gap-2">
                                <Check size={16} /> Mark as Friendly
                            </button>
                        </div>

                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
};

export default VideoModal;
