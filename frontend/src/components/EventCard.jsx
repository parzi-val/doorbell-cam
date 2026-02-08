import { Clock, AlertTriangle, Disc } from 'lucide-react';
import clsx from 'clsx';
import { format } from 'date-fns';

const EventCard = ({ event, onClick }) => {
    const date = new Date(event.timestamp * 1000);
    const timeStr = format(date, 'PP p');

    const level = event.final_level || event.trigger_level;
    const isThreat = level === 'THREAT';
    const hasWeapon = event.weapon_detected;

    return (
        <div
            onClick={() => onClick(event)}
            className="bg-card border border-border rounded-xl overflow-hidden cursor-pointer hover:translate-y-[-4px] hover:shadow-lg hover:shadow-slate-200 transition-all group"
        >
            <div className="h-40 bg-slate-100 relative flex items-center justify-center text-secondary group-hover:bg-slate-200 transition-colors">
                <Disc size={32} className="text-slate-300 group-hover:text-accent-orange transition-colors" />
                <span className="absolute bottom-2 right-2 text-xs bg-white/90 px-2 py-1 rounded text-primary font-medium shadow-sm">
                    {event.duration}s
                </span>
            </div>

            <div className="p-4">
                <div className="flex justify-between items-start mb-2">
                    <h3 className={clsx(
                        "font-bold text-lg",
                        isThreat ? "text-accent-red" : "text-accent-orange"
                    )}>
                        {level}
                    </h3>
                    {hasWeapon && (
                        <span className="bg-accent-red text-white text-[10px] font-bold px-2 py-1 rounded-full flex items-center gap-1">
                            <AlertTriangle size={12} /> WEAPON
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-2 text-sm text-secondary mb-1">
                    <Clock size={14} />
                    <span>{timeStr}</span>
                </div>

                <div className="text-xs text-secondary/60 mt-3 flex justify-between">
                    <span>ID: {event.clip_id ? event.clip_id.slice(0, 8) : 'N/A'}...</span>
                    <span>Intent: {event.max_intent.toFixed(2)}</span>
                </div>
            </div>
        </div>
    );
};

export default EventCard;
